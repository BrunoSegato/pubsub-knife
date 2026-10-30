import gzip
import json
import sys
import time
from pathlib import Path

import typer

from pubsub_knife import constants
from pubsub_knife.providers import KnifeContext
from pubsub_knife.utils import fail


def read_message(message: str | None) -> str:
    if message is None or message == "-":
        if message is None and sys.stdin.isatty():
            fail(constants.MESSAGE_PUBLISH_MISSING_MESSAGE)
        return sys.stdin.read()
    if message.startswith("@"):
        path = Path(message[1:])
        if not path.is_file():
            fail(constants.MESSAGE_PUBLISH_FILE_NOT_FOUND.format(path))
        return path.read_text()
    return message


def build_payload(
    content: str,
    validate_json: bool,
    gzip_enabled: bool
) -> tuple[bytes, dict[str, str]]:
    if validate_json:
        try:
            json.loads(content)
        except json.JSONDecodeError:
            fail(constants.MESSAGE_PUBLISH_INVALID_JSON)

    if gzip_enabled:
        return gzip.compress(content.encode()), {"encoding": "gzip"}
    return content.encode(), {}


def publish(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Nome do tópico."),
    message: str | None = typer.Argument(
        None,
        help="Mensagem a publicar. Use @arquivo para ler de um arquivo "
             "ou '-' (ou pipe) para ler do stdin.",
        show_default=False,
    ),
    validate_json: bool = typer.Option(
        False, "--json", help="Valida se a mensagem é um JSON válido."
    ),
    gzip_enabled: bool = typer.Option(
        False, "--gzip", help="Comprime a mensagem (atributo encoding=gzip)."
    ),
    repeat: int = typer.Option(
        1, "--repeat", "-r", min=1, help="Número de vezes para publicar a mensagem."
    ),
    interval: float = typer.Option(
        0, "--interval", "-i", min=0, help="Segundos de espera entre publicações."
    ),
) -> None:
    """Publica mensagens em um tópico."""
    knife: KnifeContext = ctx.obj
    content_bytes, attributes = build_payload(
        content=read_message(message),
        validate_json=validate_json,
        gzip_enabled=gzip_enabled
    )
    publisher = knife.publisher
    topic_path = knife.topic_path(topic)
    typer.echo(constants.MESSAGE_PUBLISHING.format(topic_path))

    failures = 0
    for i in range(repeat):
        start = time.perf_counter()
        future = publisher.publish(topic_path, content_bytes, **attributes)
        try:
            message_id = future.result(timeout=knife.settings.pubsub_timeout)
        except Exception as e:
            failures += 1
            typer.echo(constants.MESSAGE_PUBLISHED_ERROR.format(e), err=True)
        else:
            elapsed = time.perf_counter() - start
            typer.echo(constants.MESSAGE_PUBLISHED.format(message_id, f"{elapsed:.4f}"))

        if interval and i < repeat - 1:
            typer.echo(constants.MESSAGE_PUBLISHED_INTERVAL.format(interval))
            time.sleep(interval)

    if failures:
        raise typer.Exit(1)
