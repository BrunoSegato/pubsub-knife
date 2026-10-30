from typing import Any

import typer
from google.api_core.exceptions import AlreadyExists, NotFound
from google.pubsub_v1.types import Subscription
from rich import print as rich_print
from rich.table import Table

from pubsub_knife import constants
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


def subscription_to_dict(subscription: Subscription) -> dict[str, Any]:
    ttl = (
        subscription.expiration_policy.ttl
        if "ttl" in subscription.expiration_policy else None
    )
    return {
        "name": subscription.name,
        "topic": subscription.topic,
        "labels": dict(subscription.labels),
        "ack_deadline_seconds": subscription.ack_deadline_seconds,
        "push_endpoint": subscription.push_config.push_endpoint or None,
        "filter": subscription.filter or None,
        "dead_letter_topic": (
            subscription.dead_letter_policy.dead_letter_topic or None
        ),
        "max_delivery_attempts": (
            subscription.dead_letter_policy.max_delivery_attempts or None
        ),
        "delivery_exactly_once": subscription.enable_exactly_once_delivery,
        "ordering": subscription.enable_message_ordering,
        # sem ttl a assinatura nunca expira
        "expiration_ttl_seconds": int(ttl.total_seconds()) if ttl else None,
        "retention_seconds": int(
            subscription.message_retention_duration.total_seconds()
        ),
    }


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
        subscription = knife.subscriber.get_subscription(
            subscription=knife.subscription_path(name)
        )
    except NotFound:
        fail(constants.MESSAGE_SUBSCRIPTION_NOT_FOUND)
    data = subscription_to_dict(subscription)
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
    subscriptions = knife.subscriber.list_subscriptions(project=knife.project_path)
    if output == OutputFormat.JSON:
        print_json([subscription_to_dict(s) for s in subscriptions])
        return
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
