import gzip
from contextlib import suppress
from typing import Any

import typer
from google.api_core.exceptions import NotFound
from google.cloud.pubsub_v1.subscriber.message import Message
from google.pubsub_v1.types import PubsubMessage
from rich import print as rich_print

from pubsub_knife import constants
from pubsub_knife.providers import KnifeContext
from pubsub_knife.utils import fail, print_warning


def decode_message(message: PubsubMessage | Message) -> dict[str, Any]:
    data = message.data
    attributes = dict(message.attributes)
    if attributes.get("encoding") == "gzip":
        # se o conteúdo não for gzip de verdade, mostra como veio
        with suppress(OSError):
            data = gzip.decompress(data)
    try:
        content: str = data.decode()
    except UnicodeDecodeError:
        content = repr(data)
    return {
        "data": content,
        "id": message.message_id,
        "attributes": attributes,
        "publish_time": (
            message.publish_time.isoformat() if message.publish_time else None
        ),
    }


def pull(
    ctx: typer.Context,
    subscription: str = typer.Argument(..., help="Nome da assinatura."),
    max_messages: int = typer.Option(
        10, "--max-messages", "-n", min=1, help="Quantidade máxima de mensagens."
    ),
    ack: bool = typer.Option(False, "--ack", help="Aplica o ack nas mensagens."),
) -> None:
    """Busca mensagens de uma assinatura."""
    knife: KnifeContext = ctx.obj
    subscriber = knife.subscriber
    sub_path = knife.subscription_path(subscription)

    try:
        response = subscriber.pull(
            subscription=sub_path,
            max_messages=max_messages,
            retry=knife.settings.pubsub_retry(),
            timeout=knife.settings.pubsub_timeout
        )
    except NotFound:
        fail(constants.MESSAGE_SUBSCRIPTION_NOT_FOUND)

    if not response.received_messages:
        print_warning(constants.MESSAGE_NO_RESULT)
        return

    for i, msg in enumerate(response.received_messages, start=1):
        typer.echo(f"\nMessage {i}")
        rich_print(decode_message(msg.message))

    if ack:
        ack_ids = [m.ack_id for m in response.received_messages]
        subscriber.acknowledge(subscription=sub_path, ack_ids=ack_ids)
        typer.echo(constants.MESSAGE_CONSUMER_ALL_ACK)
