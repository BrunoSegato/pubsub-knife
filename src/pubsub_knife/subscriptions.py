import typer
from rich import print
from rich.console import Console
from rich.table import Table


app = typer.Typer(pretty_exceptions_show_locals=False)
console = Console()

@app.command()
def create(
    name: str = typer.Option(..., help="Nome da assinatura."),
    topic_name: str = typer.Option(..., help="Nome do tópico."),
    ctx: typer.Context = typer.Context
):
    settings = ctx.obj["settings"]
    subscriber = ctx.obj["default_subscriber_client"]
    topic_path = subscriber.topic_path(settings.pubsub_project_id, topic_name)
    subscription_path = subscriber.subscription_path(settings.pubsub_project_id, name)
    subscriber.create_subscription(name=subscription_path, topic=topic_path)
    data = {
        "subscription_name": subscription_path,
        "topic_name": topic_path
    }
    print("Subscription successful created.")
    print(data)


@app.command()
def delete(
    name: str = typer.Option(..., help="Nome da assinatura."),
    ctx: typer.Context = typer.Context
):
    settings = ctx.obj["settings"]
    subscriber = ctx.obj["default_subscriber_client"]
    subscription_path = subscriber.subscription_path(settings.pubsub_project_id, name)
    subscriber.delete_subscription(subscription=subscription_path)
    data = {
        "subscription_name": subscription_path,
    }
    print("Subscription successful deleted.")
    print(data)


@app.command()
def get(
    name: str = typer.Option(..., help="Nome da assinatura."),
    ctx: typer.Context = typer.Context
):
    settings = ctx.obj["settings"]
    subscriber = ctx.obj["default_subscriber_client"]
    subscription_path = subscriber.subscription_path(settings.pubsub_project_id, name)
    subscription = subscriber.get_subscription(subscription=subscription_path)
    print("Subscription Info.")
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
    print(data)


@app.command()
def list_subscriptions(ctx: typer.Context = typer.Context):
    settings = ctx.obj["settings"]
    subscriber = ctx.obj["default_subscriber_client"]
    subscriptions = subscriber.list_subscriptions(project=f"projects/{settings.pubsub_project_id}")
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
    console.print(table)
