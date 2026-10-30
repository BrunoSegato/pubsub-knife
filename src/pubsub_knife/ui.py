import typer

from pubsub_knife.providers import KnifeContext


def ui(ctx: typer.Context) -> None:
    """Abre uma interface no terminal para navegar pelos tópicos e assinaturas."""
    knife: KnifeContext = ctx.obj
    # falha aqui, com a mensagem de sempre, se o emulador não estiver de pé
    knife.publisher  # noqa: B018
    knife.subscriber  # noqa: B018

    # import tardio: o Textual soma ~60ms, que os outros comandos não precisam pagar
    from pubsub_knife.tui import KnifeApp  # noqa: PLC0415

    KnifeApp(knife).run()
