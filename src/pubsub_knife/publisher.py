import gzip
import json
import time
from typing import Any

import typer

from src import constants
from src.utils import callback

app = typer.Typer(pretty_exceptions_show_locals=False)


def get_content_and_attributes(
    message: str,
    json_message: str,
    gzip_enabled: bool
) -> tuple[bytes, dict[str, str] | Any]:
    if bool(message) == bool(json_message):
        typer.echo("Você deve fornecer apenas um dos parâmetros: --message ou --json")
        raise typer.Exit(0)

    content = message or json_message
    if json_message:
        try:
            json.loads(json_message)
        except Exception:
            typer.echo("Mensagem JSON inválida")
            raise typer.Exit(0)

    if gzip_enabled:
        content_bytes = gzip.compress(content.encode())
        attributes = {"encoding": "gzip"}
    else:
        content_bytes = content.encode()
        attributes = {}

    return content_bytes, attributes


@app.command("sync")
def publish_sync(
    topic: str = typer.Option(..., help="Nome do tópico."),
    message: str = typer.Option(None, help="Mensagem a ser publicada."),
    json_message: str = typer.Option(None, "--json"),
    gzip_enabled: bool = typer.Option(False, "--gzip"),
    repeat: int = typer.Option(1, help="Número de vezes para publicar a mensagem"),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    content_bytes, attributes = get_content_and_attributes(
        message=message,
        json_message=json_message,
        gzip_enabled=gzip_enabled
    )

    settings = ctx.obj["settings"]
    publisher = ctx.obj["default_publisher_client"]
    topic_path = publisher.topic_path(settings.pubsub_project_id, topic)

    typer.echo(constants.MESSAGE_PUBLISH_SYNC.format(topic_path))

    for _ in range(repeat):
        start = time.perf_counter()
        future = publisher.publish(topic_path, content_bytes, **attributes)
        message_id = future.result()
        elapsed = time.perf_counter() - start
        typer.echo(constants.MESSAGE_PUBLISHED.format(message_id, f"{elapsed:.4f}"))


@app.command("with-callback")
def publish_with_callback(
    topic: str = typer.Option(..., help="Nome do tópico."),
    message: str = typer.Option(None, help="Mensagem a ser publicada."),
    json_message: str = typer.Option(None, "--json"),
    gzip_enabled: bool = typer.Option(False, "--gzip"),
    repeat: int = typer.Option(1, help="Número de vezes para publicar a mensagem"),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    content_bytes, attributes = get_content_and_attributes(
        message=message,
        json_message=json_message,
        gzip_enabled=gzip_enabled
    )

    settings = ctx.obj["settings"]
    publisher = ctx.obj["batch_publisher_client"]
    topic_path = publisher.topic_path(settings.pubsub_project_id, topic)
    typer.echo(constants.MESSAGE_PUBLISH_CALLBACK.format(topic_path))

    for _ in range(repeat):
        future = publisher.publish(topic_path, content_bytes, **attributes)
        future.add_done_callback(callback)
        typer.echo(constants.MESSAGE_PUBLISH_WAIT_TO_CALLBACK)
