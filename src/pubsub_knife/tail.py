import json
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from typing import Any

import typer
from google.api_core.exceptions import NotFound
from google.cloud.pubsub_v1.subscriber.message import Message
from rich.json import JSON
from rich.markup import escape

from pubsub_knife import constants
from pubsub_knife.consumer import decode_message
from pubsub_knife.providers import KnifeContext
from pubsub_knife.utils import console, err_console, fail


def render(index: int, data: dict[str, Any], jsonl: bool) -> None:
    if jsonl:
        # print direto (sem rich) para não quebrar linhas nem colorir o JSON
        print(json.dumps(data, ensure_ascii=False), flush=True)
        return
    console.rule(
        f"[bold]#{index}[/bold] [dim]id={data['id']} {data['publish_time']}[/dim]",
        align="left",
    )
    if data["attributes"]:
        console.print(f"[cyan]attributes:[/cyan] {escape(str(data['attributes']))}")
    if "ordering_key" in data:
        console.print(f"[cyan]ordering_key:[/cyan] {escape(data['ordering_key'])}")
    try:
        console.print(JSON(data["data"]))
    except json.JSONDecodeError:
        console.print(data["data"], markup=False, highlight=False)


class Tail:
    def __init__(self, limit: int | None, ack: bool, jsonl: bool) -> None:
        self.limit = limit
        self.ack = ack
        self.jsonl = jsonl
        self.count = 0
        self.done = threading.Event()
        self._lock = threading.Lock()
        self._held: list[Message] = []

    def __call__(self, message: Message) -> None:
        with self._lock:
            if self.done.is_set():
                message.nack()
                return
            self.count += 1
            render(self.count, decode_message(message), self.jsonl)
            if self.ack:
                message.ack()
            else:
                self._held.append(message)
            if self.limit and self.count >= self.limit:
                self.done.set()

    def release(self) -> None:
        """Devolve as mensagens não confirmadas para a assinatura."""
        with self._lock:
            self.done.set()
            for message in self._held:
                message.nack()
            self._held.clear()


@contextmanager
def temporary_subscription(knife: KnifeContext, topic: str) -> Iterator[str]:
    name = f"pk-tail-{topic}-{uuid.uuid4().hex[:8]}"
    path = knife.subscription_path(name)
    try:
        knife.subscriber.create_subscription(
            name=path, topic=knife.topic_path(topic)
        )
    except NotFound:
        fail(constants.MESSAGE_TOPIC_NOT_FOUND)
    try:
        yield path
    finally:
        with suppress(NotFound):
            knife.subscriber.delete_subscription(subscription=path)


def tail(
    ctx: typer.Context,
    subscription: str | None = typer.Argument(
        None, help="Assinatura a acompanhar.", show_default=False
    ),
    topic: str | None = typer.Option(
        None, "--topic", "-t",
        help="Acompanha um tópico via assinatura temporária (removida ao sair).",
    ),
    ack: bool = typer.Option(
        False, "--ack",
        help="Confirma (consome) as mensagens. Sem isso, elas voltam para a "
             "assinatura ao sair.",
    ),
    jsonl: bool = typer.Option(
        False, "--jsonl", help="Uma mensagem JSON por linha (útil com jq)."
    ),
    limit: int | None = typer.Option(
        None, "--limit", "-n", min=1, help="Para após N mensagens."
    ),
    timeout: float | None = typer.Option(
        None, "--timeout", min=0, help="Para após N segundos."
    ),
) -> None:
    """Acompanha as mensagens de uma assinatura ou tópico em tempo real."""
    if bool(subscription) == bool(topic):
        fail(constants.MESSAGE_TAIL_TARGET)

    knife: KnifeContext = ctx.obj
    if topic:
        with temporary_subscription(knife, topic) as path:
            # a assinatura é nossa: não faz sentido devolver as mensagens
            stream(knife, path, Tail(limit, ack=True, jsonl=jsonl), timeout)
        return

    path = knife.subscription_path(subscription or "")
    try:
        knife.subscriber.get_subscription(subscription=path)
    except NotFound:
        fail(constants.MESSAGE_SUBSCRIPTION_NOT_FOUND)
    stream(knife, path, Tail(limit, ack=ack, jsonl=jsonl), timeout)


def stream(
    knife: KnifeContext,
    path: str,
    handler: Tail,
    timeout: float | None
) -> None:
    err_console.print(constants.MESSAGE_TAIL_LISTENING.format(path), soft_wrap=True)
    future = knife.subscriber.subscribe(path, callback=handler)
    future.add_done_callback(lambda _: handler.done.set())
    error: BaseException | None = None
    try:
        handler.done.wait(timeout)
        if future.done():
            error = future.exception()
    except KeyboardInterrupt:
        pass
    finally:
        handler.release()
        future.cancel()
        with suppress(Exception):
            future.result(timeout=5)
    if error:
        fail(constants.MESSAGE_TAIL_ERROR.format(error))
    err_console.print(
        constants.MESSAGE_TAIL_STOPPED.format(handler.count), soft_wrap=True
    )
