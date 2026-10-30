import typer
from google.api_core.exceptions import AlreadyExists, NotFound
from rich import print as rich_print
from rich.table import Table

from pubsub_knife import constants, services
from pubsub_knife.providers import KnifeContext
from pubsub_knife.utils import (
    Output,
    OutputFormat,
    console,
    fail,
    print_json,
    print_success,
    print_warning,
)

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.command()
def create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nome da assinatura."),
    topic: str = typer.Option(..., "--topic", "-t", help="Nome do tópico."),
    output: Output = OutputFormat.TEXT,
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
    if output == OutputFormat.JSON:
        print_json({"name": subscription_path, "status": "created"})
        return
    print_success(constants.MESSAGE_SUBSCRIPTION_CREATED.format(subscription_path))


@app.command()
def delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nome da assinatura."),
    output: Output = OutputFormat.TEXT,
) -> None:
    """Remove uma assinatura."""
    knife: KnifeContext = ctx.obj
    subscription_path = knife.subscription_path(name)
    try:
        knife.subscriber.delete_subscription(subscription=subscription_path)
    except NotFound:
        fail(constants.MESSAGE_SUBSCRIPTION_NOT_FOUND)
    if output == OutputFormat.JSON:
        print_json({"name": subscription_path, "status": "deleted"})
        return
    print_success(constants.MESSAGE_SUBSCRIPTION_DELETED.format(subscription_path))


app.command("rm", hidden=True)(delete)


@app.command()
def get(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nome da assinatura."),
    output: Output = OutputFormat.TEXT,
) -> None:
    """Mostra os detalhes de uma assinatura."""
    knife: KnifeContext = ctx.obj
    try:
        data = services.get_subscription(knife, name)
    except NotFound:
        fail(constants.MESSAGE_SUBSCRIPTION_NOT_FOUND)
    if output == OutputFormat.JSON:
        print_json(data)
        return
    rich_print(data)


@app.command("list")
def list_subscriptions(
    ctx: typer.Context,
    output: Output = OutputFormat.TEXT,
) -> None:
    """Lista as assinaturas do projeto."""
    knife: KnifeContext = ctx.obj
    subscriptions = services.list_subscriptions(knife)
    if output == OutputFormat.JSON:
        print_json(subscriptions)
        return
    if not subscriptions:
        print_warning(constants.MESSAGE_NO_RESULT)
        return
    table = Table("Name", "Topic", "Labels", "Ack Deadline (s)")
    for subscription in subscriptions:
        table.add_row(
            subscription["name"],
            subscription["topic"],
            ", ".join(f"{k}={v}" for k, v in subscription["labels"].items()),
            str(subscription["ack_deadline_seconds"]),
        )
    console.print(table)


app.command("ls", hidden=True)(list_subscriptions)
