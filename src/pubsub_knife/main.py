import typer

from src.config import settings
from src.providers import (
    get_publisher_client,
    get_publisher_with_batch_settings,
    get_subscriber_client,
)
from src.pubsub_knife import consumer, publisher, subscriptions, topics

app = typer.Typer()
app.add_typer(topics.app, name="topic")
app.add_typer(subscriptions.app, name="subscription")
app.add_typer(publisher.app, name="publisher")
app.add_typer(consumer.app, name="consumer")


@app.callback()
def main(ctx: typer.Context) -> None:
    """
    Pub/Sub Knife CLI — gerencie tópicos, assinaturas e mensagens do emulador.
    """
    ctx.obj = {
        "settings": settings,
        "default_publisher_client": get_publisher_client(),
        "default_subscriber_client": get_subscriber_client(),
        "batch_publisher_client": get_publisher_with_batch_settings()
    }


if __name__ == "__main__":
    app()
