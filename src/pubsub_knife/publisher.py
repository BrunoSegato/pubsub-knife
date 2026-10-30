import gzip
import json
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer

from pubsub_knife import constants
from pubsub_knife.providers import KnifeContext
from pubsub_knife.utils import Output, OutputFormat, fail, print_json


@dataclass(frozen=True)
class OutgoingMessage:
    data: bytes
    attributes: dict[str, str] = field(default_factory=dict)
    ordering_key: str = ""


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


def parse_attributes(values: list[str]) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for value in values:
        key, sep, val = value.partition("=")
        if not sep or not key:
            fail(constants.MESSAGE_PUBLISH_INVALID_ATTRIBUTE.format(value))
        attributes[key] = val
    return attributes


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


def parse_envelope(line: str, number: int) -> tuple[str, dict[str, str], str]:
    """
    Lê uma linha no formato gerado por `pk tail --jsonl`:
    {"data": ..., "attributes": {...}, "ordering_key": "..."}
    """
    invalid = constants.MESSAGE_PUBLISH_INVALID_ENVELOPE.format(number)
    try:
        envelope: Any = json.loads(line)
    except json.JSONDecodeError:
        fail(invalid)
    if not isinstance(envelope, dict) or "data" not in envelope:
        fail(invalid)
    data = envelope["data"]
    attributes = envelope.get("attributes") or {}
    if not isinstance(attributes, dict):
        fail(invalid)
    content = data if isinstance(data, str) else json.dumps(data)
    return (
        content,
        {str(k): str(v) for k, v in attributes.items()},
        str(envelope.get("ordering_key") or ""),
    )


def build_messages(
    content: str,
    *,
    lines: bool = False,
    envelope: bool = False,
    validate_json: bool = False,
    gzip_enabled: bool = False,
    attributes: dict[str, str] | None = None,
    ordering_key: str = ""
) -> list[OutgoingMessage]:
    attributes = attributes or {}
    if gzip_enabled and attributes.get("encoding", "gzip") != "gzip":
        fail(constants.MESSAGE_PUBLISH_ENCODING_CONFLICT)

    if lines or envelope:
        bodies = [
            (number, line)
            for number, line in enumerate(content.splitlines(), start=1)
            if line.strip()
        ]
        if not bodies:
            fail(constants.MESSAGE_PUBLISH_EMPTY_INPUT)
    else:
        bodies = [(1, content)]

    messages = []
    for number, body in bodies:
        text, msg_key = body, ""
        msg_attributes: dict[str, str] = {}
        if envelope:
            text, msg_attributes, msg_key = parse_envelope(body, number)
        # envelope capturado com gzip volta a ser comprimido, mantendo o round-trip
        compress = gzip_enabled or msg_attributes.get("encoding") == "gzip"
        data, payload_attributes = build_payload(text, validate_json, compress)
        messages.append(OutgoingMessage(
            data=data,
            attributes={**msg_attributes, **attributes, **payload_attributes},
            ordering_key=msg_key or ordering_key,
        ))
    return messages


def publish(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Nome do tópico."),
    message: str | None = typer.Argument(
        None,
        help="Mensagem a publicar. Use @arquivo para ler de um arquivo "
             "ou '-' (ou pipe) para ler do stdin.",
        show_default=False,
    ),
    attr: list[str] = typer.Option(
        [], "--attr", "-a", help="Atributo no formato chave=valor (repetível)."
    ),
    ordering_key: str = typer.Option(
        "", "--ordering-key", "-k", help="Ordering key das mensagens."
    ),
    lines: bool = typer.Option(
        False, "--lines", help="Publica cada linha da entrada como uma mensagem."
    ),
    envelope: bool = typer.Option(
        False, "--envelope",
        help="Cada linha é um JSON {data, attributes, ordering_key}, "
             "como gerado por `pk tail --jsonl`.",
    ),
    validate_json: bool = typer.Option(
        False, "--json", help="Valida se cada mensagem é um JSON válido."
    ),
    gzip_enabled: bool = typer.Option(
        False, "--gzip", help="Comprime as mensagens (atributo encoding=gzip)."
    ),
    repeat: int = typer.Option(
        1, "--repeat", "-r", min=1, help="Número de vezes para publicar a entrada."
    ),
    interval: float = typer.Option(
        0, "--interval", "-i", min=0, help="Segundos de espera entre publicações."
    ),
    output: Output = OutputFormat.TEXT,
) -> None:
    """Publica mensagens em um tópico."""
    knife: KnifeContext = ctx.obj
    messages = build_messages(
        read_message(message),
        lines=lines,
        envelope=envelope,
        validate_json=validate_json,
        gzip_enabled=gzip_enabled,
        attributes=parse_attributes(attr),
        ordering_key=ordering_key,
    ) * repeat
    publisher = knife.publisher
    topic_path = knife.topic_path(topic)
    as_json = output == OutputFormat.JSON

    def echo(text: str) -> None:
        # no modo json o stdout é só o resultado final
        if not as_json:
            typer.echo(text)

    echo(constants.MESSAGE_PUBLISHING.format(topic_path))

    def send(msg: OutgoingMessage) -> Any:
        return publisher.publish(
            topic_path, msg.data, ordering_key=msg.ordering_key, **msg.attributes
        )

    timeout = knife.settings.pubsub_timeout
    start = time.perf_counter()
    results: list[PublishResult] = []
    if interval:
        # um por vez, respeitando o intervalo
        for i, msg in enumerate(messages):
            sent = time.perf_counter()
            results.append(wait_result(send(msg), sent, timeout, echo))
            if i < len(messages) - 1:
                echo(constants.MESSAGE_PUBLISHED_INTERVAL.format(interval))
                time.sleep(interval)
    else:
        # todos de uma vez: o client agrupa em batches
        futures = [send(msg) for msg in messages]
        results = [wait_result(f, start, timeout, echo) for f in futures]

    message_ids = [r.message_id for r in results if r.message_id]
    errors = [r.error for r in results if r.error]
    elapsed = f"{time.perf_counter() - start:.4f}"
    if as_json:
        print_json({
            "topic": topic_path,
            "message_ids": message_ids,
            "errors": errors,
            "elapsed_seconds": float(elapsed),
        })
    elif len(messages) > 1:
        echo(constants.MESSAGE_PUBLISHED_SUMMARY.format(len(message_ids), elapsed))
    if errors:
        raise typer.Exit(1)


@dataclass(frozen=True)
class PublishResult:
    message_id: str = ""
    error: str = ""


def wait_result(
    future: Any,
    start: float,
    timeout: float,
    echo: Callable[[str], None]
) -> PublishResult:
    try:
        message_id = future.result(timeout=timeout)
    except Exception as e:
        # o erro vai para o stderr mesmo no modo json
        typer.echo(constants.MESSAGE_PUBLISHED_ERROR.format(e), err=True)
        return PublishResult(error=str(e))
    elapsed = time.perf_counter() - start
    echo(constants.MESSAGE_PUBLISHED.format(message_id, f"{elapsed:.4f}"))
    return PublishResult(message_id=message_id)
