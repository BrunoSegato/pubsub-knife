import json
from typing import Any, ClassVar

from google.api_core.exceptions import GoogleAPICallError
from rich.console import Group, RenderableType
from rich.json import JSON
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, RichLog, Static, Tree

from pubsub_knife import services
from pubsub_knife.providers import KnifeContext

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


class KnifeApp(App[None]):
    """Navega pelos tópicos e assinaturas do emulador (somente leitura)."""

    TITLE = "PubSub Knife"
    CSS = """
    #resources { width: 40%; border: round $primary; }
    #side { width: 1fr; }
    #details { height: auto; border: round $primary; padding: 0 1; }
    #messages { height: 1fr; border: round $primary; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "reload", "Atualizar"),
        ("p", "peek", "Espiar mensagens"),
        ("q", "quit", "Sair"),
    ]

    def __init__(self, knife: KnifeContext) -> None:
        super().__init__()
        self.knife = knife

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Tree(self.knife.project_path, id="resources")
            with Vertical(id="side"):
                yield Static("Selecione um tópico ou assinatura.", id="details")
                yield RichLog(id="messages", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = (
            f"{self.knife.project_id} @ {self.knife.settings.pubsub_emulator_host}"
        )
        tree = self.query_one(Tree)
        tree.border_title = "Recursos"
        self.query_one("#details", Static).border_title = "Detalhes"
        self.query_one(RichLog).border_title = "Mensagens"
        tree.focus()
        self.load_resources()

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

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[Any]) -> None:
        data = event.node.data
        details = self.query_one("#details", Static)
        if not data:
            details.update("Selecione um tópico ou assinatura.")
            return
        details.update(details_table(data))
        log = self.query_one(RichLog)
        log.clear()
        if data["kind"] == "subscription" and not data["push_endpoint"]:
            log.write(Text("p para espiar as mensagens.", style="dim"))

    def action_reload(self) -> None:
        self.load_resources()

    def action_peek(self) -> None:
        node = self.query_one(Tree).cursor_node
        data = node.data if node else None
        if not data or data["kind"] != "subscription":
            self.notify("Selecione uma assinatura.", severity="warning")
            return
        if data["push_endpoint"]:
            # o emulador está entregando essas mensagens ao endpoint
            self.notify(
                "Assinatura push: as mensagens vão para o endpoint. Para vê-las, "
                f"use pk tail -t {short_name(data['topic'])}.",
                severity="warning",
            )
            return
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
