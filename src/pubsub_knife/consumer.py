import typer
from rich import print as rich_print

from src import constants

app = typer.Typer(pretty_exceptions_show_locals=False)


@app.command("pull")
def pull_messages(
    subscription: str = typer.Option(..., help="Nome da assinatura."),
    max_messages: int = typer.Option(..., help="Quantidade de mensagens."),
    auto_ack: bool = typer.Option(False, help="Aplicar o ack nas mensagens."),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    settings = ctx.obj["settings"]
    subscriber = ctx.obj["default_subscriber_client"]

    sub_path = subscriber.subscription_path(settings.pubsub_project_id, subscription)
    retry = settings.pubsub_retry()

    response = subscriber.pull(
        subscription=sub_path,
        max_messages=max_messages,
        retry=retry,
        timeout=settings.pubsub_timeout
    )

    if not response.received_messages:
        typer.echo(constants.MESSAGE_NO_RESULT)
        return

    for i, msg in enumerate(response.received_messages, start=1):
        typer.echo(f"\nMessage {i}")
        data = {
            "data": msg.message.data.decode(),
            "id": msg.message.message_id,
            "attr": msg.message.attributes
        }
        rich_print(data)

    if auto_ack:
        ack_ids = [m.ack_id for m in response.received_messages]
        subscriber.acknowledge(subscription=sub_path, ack_ids=ack_ids)
        typer.echo(constants.MESSAGE_CONSUMER_ALL_ACK)
