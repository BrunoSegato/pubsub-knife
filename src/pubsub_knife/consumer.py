import typer
from google.api_core.exceptions import NotFound
from rich import print as rich_print

from pubsub_knife import constants, services
from pubsub_knife.providers import KnifeContext
from pubsub_knife.utils import Output, OutputFormat, fail, print_json, print_warning


def pull(
    ctx: typer.Context,
    subscription: str = typer.Argument(..., help="Nome da assinatura."),
    max_messages: int = typer.Option(
        10, "--max-messages", "-n", min=1, help="Quantidade máxima de mensagens."
    ),
    ack: bool = typer.Option(False, "--ack", help="Aplica o ack nas mensagens."),
    output: Output = OutputFormat.TEXT,
) -> None:
    """Busca mensagens de uma assinatura."""
    knife: KnifeContext = ctx.obj
    try:
        messages = services.pull(knife, subscription, max_messages, ack=ack)
    except NotFound:
        fail(constants.MESSAGE_SUBSCRIPTION_NOT_FOUND)

    as_json = output == OutputFormat.JSON
    if as_json:
        print_json(messages)
    elif not messages:
        print_warning(constants.MESSAGE_NO_RESULT)
        return
    else:
        for i, decoded in enumerate(messages, start=1):
            typer.echo(f"\nMessage {i}")
            rich_print(decoded)

    if ack and messages:
        # no modo json o stdout é só o JSON
        typer.echo(constants.MESSAGE_CONSUMER_ALL_ACK, err=as_json)
