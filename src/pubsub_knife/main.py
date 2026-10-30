import typer

from pubsub_knife import (
    apply,
    consumer,
    export,
    publisher,
    subscriptions,
    tail,
    topics,
    ui,
)
from pubsub_knife.config import Settings
from pubsub_knife.providers import KnifeContext

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)
app.add_typer(topics.app, name="topic", help="Gerencia tópicos.")
app.add_typer(subscriptions.app, name="subscription", help="Gerencia assinaturas.")
app.add_typer(subscriptions.app, name="sub", hidden=True)
app.command("pub")(publisher.publish)
app.command("pull")(consumer.pull)
app.command("apply")(apply.apply)
app.command("export")(export.export)
app.command("tail")(tail.tail)
app.command("ui")(ui.ui)


@app.callback()
def main(
    ctx: typer.Context,
    project: str | None = typer.Option(
        None, "--project", "-p",
        help="Projeto do emulador. Também lido de PUBSUB_PROJECT_ID ou do .env.",
        show_default="dummy-project"
    ),
    emulator_host: str | None = typer.Option(
        None, "--emulator-host",
        help="Endereço do emulador. Também lido de PUBSUB_EMULATOR_HOST ou do .env.",
        show_default="localhost:8085"
    ),
) -> None:
    """
    Pub/Sub Knife CLI — gerencie tópicos, assinaturas e mensagens do emulador.
    """
    settings = Settings()
    if project:
        settings.pubsub_project_id = project
    if emulator_host:
        settings.pubsub_emulator_host = emulator_host
    ctx.obj = KnifeContext(settings, project_overridden=bool(project))


if __name__ == "__main__":
    app()
