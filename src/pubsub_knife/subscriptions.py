import typer
from google.api_core.exceptions import AlreadyExists, NotFound
from rich import print as rich_print
from rich.console import Console
from rich.table import Table

from src import constants
from src.utils import print_error, print_success, print_warning

app = typer.Typer(pretty_exceptions_show_locals=False)

@app.command()
def create(
    name: str = typer.Option(..., help="Nome da assinatura."),
    topic_name: str = typer.Option(..., help="Nome do tópico."),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    settings = ctx.obj["settings"]
    subscriber = ctx.obj["default_subscriber_client"]
    topic_path = subscriber.topic_path(settings.pubsub_project_id, topic_name)
    subscription_path = subscriber.subscription_path(settings.pubsub_project_id, name)
    try:
        subscriber.create_subscription(name=subscription_path, topic=topic_path)
    except AlreadyExists:
        print_error(constants.MESSAGE_SUBSCRIPTION_IS_ALREADY_EXISTS)
    else:
        print_success(constants.MESSAGE_SUBSCRIPTION_CREATED.format(subscription_path))


@app.command()
def delete(
    name: str = typer.Option(..., help="Nome da assinatura."),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    settings = ctx.obj["settings"]
    subscriber = ctx.obj["default_subscriber_client"]
    subscription_path = subscriber.subscription_path(settings.pubsub_project_id, name)
    try:
        subscriber.delete_subscription(subscription=subscription_path)
    except NotFound:
        print_error(constants.MESSAGE_SUBSCRIPTION_NOT_FOUND)
    else:
        print_success(constants.MESSAGE_SUBSCRIPTION_DELETED.format(subscription_path))


@app.command()
def get(
    name: str = typer.Option(..., help="Nome da assinatura."),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    settings = ctx.obj["settings"]
    subscriber = ctx.obj["default_subscriber_client"]
    subscription_path = subscriber.subscription_path(settings.pubsub_project_id, name)
    try:
        subscription = subscriber.get_subscription(subscription=subscription_path)
    except NotFound:
        print_error(constants.MESSAGE_SUBSCRIPTION_NOT_FOUND)
    else:
        data = {
            "subscription_name": subscription.name,
            "topic": subscription.topic,
            "labels": "",
            "ack_confirmation": str(subscription.ack_deadline_seconds),
            "delivery_exactly_once": str(subscription.enable_exactly_once_delivery),
            "expiration_policy": str(subscription.expiration_policy),
            "ordering": str(subscription.enable_message_ordering),
            "retention_policy": str(subscription.message_retention_duration)
        }
        rich_print(data)


@app.command()
def list_subscriptions(ctx: typer.Context = typer.Option(..., hidden=True)) -> None:
    settings = ctx.obj["settings"]
    subscriber = ctx.obj["default_subscriber_client"]
    subscriptions = subscriber.list_subscriptions(
        project=f"projects/{settings.pubsub_project_id}"
    )
    table = Table(
        "Name",
        "Topic",
        "Labels",
        "Ack Confirmation"
    )
    for subscription in subscriptions:
        table.add_row(
            subscription.name,
            subscription.topic,
            "",
            str(subscription.ack_deadline_seconds),
        )
    if not table.row_count:
        print_warning(constants.MESSAGE_NO_RESULT)
        return
    console = Console()
    console.print(table)
