import typer
from google.api_core.exceptions import AlreadyExists, NotFound
from rich import print as rich_print
from rich.table import Table

from pubsub_knife import constants
from pubsub_knife.providers import KnifeContext
from pubsub_knife.utils import console, fail, print_success, print_warning

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.command()
def create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nome da assinatura."),
    topic: str = typer.Option(..., "--topic", "-t", help="Nome do tópico."),
) -> None:
    """Cria uma assinatura (pull) para um tópico."""
    knife: KnifeContext = ctx.obj
    subscription_path = knife.subscription_path(name)
    try:
        knife.subscriber.create_subscription(
            name=subscription_path, topic=knife.topic_path(topic)
        )
    except AlreadyExists:
        fail(constants.MESSAGE_SUBSCRIPTION_IS_ALREADY_EXISTS)
    except NotFound:
        fail(constants.MESSAGE_TOPIC_NOT_FOUND)
    print_success(constants.MESSAGE_SUBSCRIPTION_CREATED.format(subscription_path))


@app.command()
def delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nome da assinatura."),
) -> None:
    """Remove uma assinatura."""
    knife: KnifeContext = ctx.obj
    subscription_path = knife.subscription_path(name)
    try:
        knife.subscriber.delete_subscription(subscription=subscription_path)
    except NotFound:
        fail(constants.MESSAGE_SUBSCRIPTION_NOT_FOUND)
    print_success(constants.MESSAGE_SUBSCRIPTION_DELETED.format(subscription_path))


app.command("rm", hidden=True)(delete)


@app.command()
def get(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nome da assinatura."),
) -> None:
    """Mostra os detalhes de uma assinatura."""
    knife: KnifeContext = ctx.obj
    try:
        subscription = knife.subscriber.get_subscription(
            subscription=knife.subscription_path(name)
        )
    except NotFound:
        fail(constants.MESSAGE_SUBSCRIPTION_NOT_FOUND)
    data = {
        "subscription_name": subscription.name,
        "topic": subscription.topic,
        "labels": dict(subscription.labels),
        "ack_deadline_seconds": subscription.ack_deadline_seconds,
        "delivery_exactly_once": subscription.enable_exactly_once_delivery,
        "expiration_policy": str(subscription.expiration_policy),
        "ordering": subscription.enable_message_ordering,
        "retention_policy": str(subscription.message_retention_duration)
    }
    rich_print(data)


@app.command("list")
def list_subscriptions(ctx: typer.Context) -> None:
    """Lista as assinaturas do projeto."""
    knife: KnifeContext = ctx.obj
    subscriptions = knife.subscriber.list_subscriptions(project=knife.project_path)
    table = Table("Name", "Topic", "Labels", "Ack Deadline (s)")
    for subscription in subscriptions:
        table.add_row(
            subscription.name,
            subscription.topic,
            ", ".join(f"{k}={v}" for k, v in subscription.labels.items()),
            str(subscription.ack_deadline_seconds),
        )
    if not table.row_count:
        print_warning(constants.MESSAGE_NO_RESULT)
        return
    console.print(table)


app.command("ls", hidden=True)(list_subscriptions)
