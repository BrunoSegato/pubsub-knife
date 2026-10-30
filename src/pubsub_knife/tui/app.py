import json
from collections import Counter
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud.pubsub_v1.subscriber.message import Message
from rich.console import Group, RenderableType
from rich.json import JSON
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, RichLog, Static, Tree

from pubsub_knife import services
from pubsub_knife.apply import SpecError, Status, apply_spec, read_spec
from pubsub_knife.providers import KnifeContext
from pubsub_knife.tui.screens import ConfirmScreen, Field, FormScreen

PEEK_LIMIT = 10
# nome que o Pub/Sub dá ao tópico de uma assinatura cujo tópico foi removido
DELETED_TOPIC = "_deleted-topic_"


def short_name(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def format_value(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items()) or "-"
    return "-" if value is None else str(value)


def details_table(data: dict[str, Any]) -> Table:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="cyan", no_wrap=True)
    table.add_column()
    for key, value in data.items():
        if key != "kind":
            table.add_row(key, Text(format_value(value)))
    return table


def render_message(index: int, message: dict[str, Any]) -> RenderableType:
    parts: list[RenderableType] = [
        Rule(f"#{index} id={message['id']} {message['publish_time']}", align="left")
    ]
    if message["attributes"]:
        parts.append(Text(f"attributes: {message['attributes']}", style="cyan"))
    if "ordering_key" in message:
        parts.append(Text(f"ordering_key: {message['ordering_key']}", style="cyan"))
    try:
        parts.append(JSON(message["data"]))
    except json.JSONDecodeError:
        parts.append(Text(message["data"]))
    return Group(*parts)


def parse_attributes(text: str) -> dict[str, str]:
    """'a=1, b=2' -> {'a': '1', 'b': '2'}. ValueError se algum item não tiver '='."""
    attributes: dict[str, str] = {}
    for item in filter(None, (part.strip() for part in text.split(","))):
        key, sep, value = item.partition("=")
        if not sep or not key.strip():
            raise ValueError(item)
        attributes[key.strip()] = value.strip()
    return attributes


def required(**labels: str) -> Callable[[dict[str, str]], str | None]:
    """Valida campos obrigatórios: required(name="Nome")."""
    def validate(values: dict[str, str]) -> str | None:
        missing = [label for name, label in labels.items() if not values[name]]
        return f"Preencha: {', '.join(missing)}." if missing else None
    return validate


def validate_publish(values: dict[str, str]) -> str | None:
    if not values["data"] and not values["attributes"]:
        return "Informe a mensagem ou ao menos um atributo."
    try:
        parse_attributes(values["attributes"])
    except ValueError as e:
        return f"Atributo inválido '{e}'. Use chave=valor, separados por vírgula."
    return None


def apply_summary(resources: list[dict[str, Any]]) -> str:
    counts = Counter(r["status"] for r in resources)
    labels = {
        Status.CREATED: "criados",
        Status.RECREATED: "recriados",
        Status.EXISTS: "já existiam",
        Status.FAILED: "falharam",
    }
    return ", ".join(f"{counts[s]} {label}" for s, label in labels.items() if counts[s])


@dataclass(eq=False)
class LiveTail:
    """Acompanhamento de um tópico por uma assinatura temporária."""
    topic: str
    path: str = ""
    future: Any = None
    count: int = 0


class KnifeApp(App[None]):
    """Navega e gerencia os tópicos e assinaturas do emulador."""

    TITLE = "PubSub Knife"
    CSS = """
    #resources { width: 40%; border: round $primary; }
    #side { width: 1fr; }
    #details { height: auto; border: round $primary; padding: 0 1; }
    #messages { height: 1fr; border: round $primary; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("t", "live", "Ao vivo"),
        Binding("p", "peek", "Espiar"),
        Binding("m", "publish", "Publicar"),
        Binding("c", "create_topic", "Novo tópico"),
        Binding("s", "create_subscription", "Nova assinatura"),
        Binding("d", "delete", "Remover"),
        Binding("a", "apply", "Aplicar yaml"),
        Binding("g", "switch_project", "Projeto"),
        Binding("r", "reload", "Atualizar"),
        Binding("q", "quit", "Sair"),
    ]

    def __init__(
        self,
        knife: KnifeContext,
        spec_file: Path = Path("pubsub.yaml")
    ) -> None:
        super().__init__()
        self.knife = knife
        self.spec_file = spec_file
        self.live: LiveTail | None = None
        self.topic_names: list[str] = []
        self.projects: list[str] = [knife.project_id]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Tree(self.knife.project_path, id="resources")
            with Vertical(id="side"):
                yield Static("Selecione um tópico ou assinatura.", id="details")
                yield RichLog(id="messages", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        tree = self.query_one(Tree)
        tree.border_title = "Recursos"
        self.query_one("#details", Static).border_title = "Detalhes"
        self.query_one(RichLog).border_title = "Mensagens"
        self.update_titles()
        tree.focus()
        self.load_resources()

    def on_unmount(self) -> None:
        if self.live:
            self.close_live(self.live)

    def update_titles(self) -> None:
        self.sub_title = (
            f"{self.knife.project_id} @ {self.knife.settings.pubsub_emulator_host}"
        )
        self.query_one(Tree).root.set_label(self.knife.project_path)

    # ---- recursos ---------------------------------------------------------

    @work(thread=True, exclusive=True, group="load")
    def load_resources(self) -> None:
        try:
            topics = services.list_topics(self.knife)
            subscriptions = services.list_subscriptions(self.knife)
        except GoogleAPICallError as e:
            self.call_from_thread(self.notify, str(e), severity="error")
            return
        self.call_from_thread(self.populate, topics, subscriptions)

    def populate(
        self,
        topics: list[dict[str, Any]],
        subscriptions: list[dict[str, Any]]
    ) -> None:
        tree: Tree[dict[str, Any]] = self.query_one(Tree)
        tree.clear()
        self.topic_names = [short_name(t["name"]) for t in topics]
        by_topic: dict[str, list[dict[str, Any]]] = {}
        for sub in subscriptions:
            by_topic.setdefault(sub["topic"], []).append(sub)

        for topic in topics:
            node = tree.root.add(
                short_name(topic["name"]), data={"kind": "topic", **topic}, expand=True
            )
            for sub in by_topic.get(topic["name"], []):
                node.add_leaf(
                    short_name(sub["name"]), data={"kind": "subscription", **sub}
                )

        orphans = by_topic.get(DELETED_TOPIC, [])
        if orphans:
            node = tree.root.add(Text("(tópico removido)", style="dim"), expand=True)
            for sub in orphans:
                node.add_leaf(
                    short_name(sub["name"]), data={"kind": "subscription", **sub}
                )

        if not tree.root.children:
            tree.root.add_leaf(Text("nenhum tópico", style="dim"))
        tree.root.expand()

    def selected(self) -> dict[str, Any] | None:
        node = self.query_one(Tree).cursor_node
        return node.data if node else None

    def selected_topic(self) -> str | None:
        """Tópico selecionado, ou o tópico da assinatura selecionada."""
        data = self.selected()
        if not data:
            return None
        if data["kind"] == "topic":
            return short_name(data["name"])
        if data["topic"] == DELETED_TOPIC:
            return None
        return short_name(data["topic"])

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[Any]) -> None:
        data = event.node.data
        details = self.query_one("#details", Static)
        if not data:
            details.update("Selecione um tópico ou assinatura.")
            return
        details.update(details_table(data))
        if self.live:
            # o painel de mensagens é do acompanhamento ao vivo
            return
        log = self.query_one(RichLog)
        log.clear()
        if data["kind"] == "subscription" and not data["push_endpoint"]:
            log.write(Text("p para espiar as mensagens.", style="dim"))

    def action_reload(self) -> None:
        self.load_resources()

    # ---- mensagens --------------------------------------------------------

    def action_peek(self) -> None:
        data = self.selected()
        if not data or data["kind"] != "subscription":
            self.notify("Selecione uma assinatura.", severity="warning")
            return
        if data["push_endpoint"]:
            # o emulador está entregando essas mensagens ao endpoint
            self.notify(
                "Assinatura push: as mensagens vão para o endpoint. Para vê-las, "
                "use t (ao vivo) no tópico.",
                severity="warning",
            )
            return
        self.stop_live()
        self.peek_messages(short_name(data["name"]))

    @work(thread=True, exclusive=True, group="peek")
    def peek_messages(self, subscription: str) -> None:
        try:
            # devolve na hora para a assinatura: espiar não consome
            messages = services.pull(
                self.knife, subscription, PEEK_LIMIT, release=True
            )
        except GoogleAPICallError as e:
            self.call_from_thread(self.notify, str(e), severity="error")
            return
        self.call_from_thread(self.show_messages, messages)

    def show_messages(self, messages: list[dict[str, Any]]) -> None:
        log = self.query_one(RichLog)
        log.clear()
        if not messages:
            log.write(Text("Nenhuma mensagem disponível.", style="dim"))
            return
        for index, message in enumerate(messages, start=1):
            log.write(render_message(index, message))

    # ---- ao vivo ----------------------------------------------------------

    def action_live(self) -> None:
        if self.live:
            self.stop_live()
            return
        topic = self.selected_topic()
        if not topic:
            self.notify("Selecione um tópico ou assinatura.", severity="warning")
            return
        self.live = LiveTail(topic)
        log = self.query_one(RichLog)
        log.clear()
        log.border_title = f"Ao vivo: {topic}"
        log.write(Text(f"Aguardando mensagens em {topic} (t para parar)...", "dim"))
        self.open_live(self.live)

    @work(thread=True, group="live")
    def open_live(self, live: LiveTail) -> None:
        try:
            live.path = services.create_temporary_subscription(self.knife, live.topic)
        except GoogleAPICallError as e:
            self.call_from_thread(self.notify, str(e), severity="error")
            self.call_from_thread(self.stop_live)
            return

        def receive(message: Message) -> None:
            message.ack()
            # o app pode ter fechado enquanto a mensagem chegava
            with suppress(RuntimeError):
                self.call_from_thread(
                    self.append_live, live, services.decode_message(message)
                )

        live.future = self.knife.subscriber.subscribe(live.path, callback=receive)
        if self.live is not live:
            # parado enquanto a assinatura era criada
            self.close_live(live)

    def append_live(self, live: LiveTail, message: dict[str, Any]) -> None:
        if self.live is not live:
            return
        log = self.query_one(RichLog)
        if not live.count:
            log.clear()
        live.count += 1
        log.write(render_message(live.count, message))

    def stop_live(self) -> None:
        live, self.live = self.live, None
        if not live:
            return
        self.query_one(RichLog).border_title = "Mensagens"
        self.notify(f"Acompanhamento de {live.topic} encerrado.")
        self.close_live_in_background(live)

    @work(thread=True, group="live")
    def close_live_in_background(self, live: LiveTail) -> None:
        self.close_live(live)

    def close_live(self, live: LiveTail) -> None:
        if live.future:
            live.future.cancel()
            with suppress(Exception):
                live.future.result(timeout=5)
        if live.path:
            with suppress(NotFound):
                self.knife.subscriber.delete_subscription(subscription=live.path)

    # ---- ações ------------------------------------------------------------

    @work(thread=True, group="action")
    def execute(self, action: Callable[[], str]) -> None:
        """Executa uma operação no emulador, avisa o resultado e recarrega."""
        try:
            message = action()
        except GoogleAPICallError as e:
            self.call_from_thread(self.notify, e.message or str(e), severity="error")
            return
        self.call_from_thread(self.notify, message)
        self.call_from_thread(self.load_resources)

    def action_create_topic(self) -> None:
        def create(values: dict[str, str] | None) -> None:
            if values:
                name = values["name"]
                self.execute(
                    lambda: f"Tópico {services.create_topic(self.knife, name)} criado."
                )

        self.push_screen(
            FormScreen("Novo tópico", [Field("name", "Nome")], required(name="Nome")),
            create,
        )

    def action_create_subscription(self) -> None:
        def create(values: dict[str, str] | None) -> None:
            if not values:
                return
            name, topic = values["name"], values["topic"]

            def send() -> str:
                path = services.create_subscription(self.knife, name, topic)
                return f"Assinatura {path} criada."

            self.execute(send)

        topic = self.selected_topic() or ""
        self.push_screen(
            FormScreen(
                "Nova assinatura (pull)",
                [
                    Field("name", "Nome", placeholder=f"{topic}-sub" if topic else ""),
                    Field(
                        "topic", "Tópico", value=topic,
                        suggestions=tuple(self.topic_names),
                    ),
                ],
                required(name="Nome", topic="Tópico"),
            ),
            create,
        )

    def action_delete(self) -> None:
        data = self.selected()
        if not data:
            self.notify("Selecione um tópico ou assinatura.", severity="warning")
            return
        name = short_name(data["name"])
        is_topic = data["kind"] == "topic"
        if is_topic:
            question = (
                f"Remover o tópico {name}?\n"
                "As assinaturas dele continuam existindo, sem tópico."
            )
        else:
            question = f"Remover a assinatura {name}?"

        def delete() -> str:
            if is_topic:
                return f"Tópico {services.delete_topic(self.knife, name)} removido."
            path = services.delete_subscription(self.knife, name)
            return f"Assinatura {path} removida."

        def confirm(confirmed: bool | None) -> None:
            if confirmed:
                self.execute(delete)

        self.push_screen(ConfirmScreen(question), confirm)

    def action_publish(self) -> None:
        topic = self.selected_topic()
        if not topic:
            self.notify("Selecione um tópico ou assinatura.", severity="warning")
            return

        def publish(values: dict[str, str] | None) -> None:
            if not values:
                return
            data = values["data"].encode()
            attributes = parse_attributes(values["attributes"])
            ordering_key = values["ordering_key"]

            def send() -> str:
                message_id = services.publish(
                    self.knife, topic, data, attributes, ordering_key
                )
                return f"Mensagem publicada em {topic}: id {message_id}."

            self.execute(send)

        self.push_screen(
            FormScreen(
                f"Publicar em {topic} (ctrl+s para enviar)",
                [
                    Field("data", "Mensagem", multiline=True),
                    Field(
                        "attributes", "Atributos",
                        placeholder="chave=valor, outra=valor",
                    ),
                    Field("ordering_key", "Ordering key"),
                ],
                validate_publish,
            ),
            publish,
        )

    def action_apply(self) -> None:
        self.apply_file()

    @work(thread=True, exclusive=True, group="apply")
    def apply_file(self) -> None:
        try:
            spec = read_spec(self.spec_file)
        except SpecError as e:
            self.call_from_thread(self.notify, str(e), severity="error")
            return
        # mesma regra do pk apply: --project (ou a troca pela UI) vence o arquivo
        project = spec.project
        overridden = self.knife.project_overridden
        if project and project != self.knife.project_id and not overridden:
            self.call_from_thread(self.switch_project, project)
        if not spec.topics:
            self.call_from_thread(
                self.notify, f"Nenhum tópico em {self.spec_file}.", severity="warning"
            )
            return
        resources = apply_spec(self.knife, spec)
        failed = [r for r in resources if r["status"] == Status.FAILED]
        summary = f"{self.spec_file} aplicado: {apply_summary(resources)}."
        if failed:
            details = "\n".join(f"{r['name']}: {r['detail']}" for r in failed)
            self.call_from_thread(
                self.notify, f"{summary}\n{details}", severity="error", timeout=15
            )
        else:
            self.call_from_thread(self.notify, summary)
        self.call_from_thread(self.load_resources)

    # ---- projeto ----------------------------------------------------------

    def action_switch_project(self) -> None:
        def switch(values: dict[str, str] | None) -> None:
            if values and values["project"] != self.knife.project_id:
                self.switch_project(values["project"])
                # escolha explícita: um pubsub.yaml com outro projeto não muda mais
                self.knife.project_overridden = True

        self.push_screen(
            FormScreen(
                "Trocar de projeto",
                [Field(
                    "project", "Projeto", value=self.knife.project_id,
                    suggestions=tuple(self.projects),
                )],
                required(project="Projeto"),
            ),
            switch,
        )

    def switch_project(self, project: str) -> None:
        self.stop_live()
        self.knife.settings.pubsub_project_id = project
        if project not in self.projects:
            self.projects.append(project)
        self.update_titles()
        self.query_one("#details", Static).update("Selecione um tópico ou assinatura.")
        self.query_one(RichLog).clear()
        self.load_resources()
