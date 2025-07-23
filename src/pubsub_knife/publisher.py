import time

import typer

from src import constants
from src.utils import callback

app = typer.Typer(pretty_exceptions_show_locals=False)


@app.command("sync")
def publish_sync(
    topic: str = typer.Option(..., help="Nome do tópico."),
    message: str = typer.Option(..., help="Mensagem a ser publicada."),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    settings = ctx.obj["settings"]
    publisher = ctx.obj["default_publisher_client"]
    topic_path = publisher.topic_path(settings.pubsub_project_id, topic)

    typer.echo(constants.MESSAGE_PUBLISH_SYNC.format(topic_path))
    start = time.perf_counter()
    future = publisher.publish(topic_path, message.encode("utf-8"))
    message_id = future.result()
    elapsed = time.perf_counter() - start
    typer.echo(constants.MESSAGE_PUBLISHED.format(message_id, f"{elapsed:.4f}"))


@app.command("with-callback")
def publish_with_callback(
    topic: str = typer.Option(..., help="Nome do tópico."),
    message: str = typer.Option(..., help="Mensagem a ser publicada."),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    settings = ctx.obj["settings"]
    publisher = ctx.obj["batch_publisher_client"]
    topic_path = publisher.topic_path(settings.pubsub_project_id, topic)

    typer.echo(constants.MESSAGE_PUBLISH_CALLBACK.format(topic_path))
    future = publisher.publish(topic_path, message.encode("utf-8"))
    future.add_done_callback(callback)
    typer.echo(constants.MESSAGE_PUBLISH_WAIT_TO_CALLBACK)
    future.result()
