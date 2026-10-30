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
    name: str = typer.Argument(..., help="Nome do tópico."),
    output: Output = OutputFormat.TEXT,
) -> None:
    """Cria um tópico."""
    knife: KnifeContext = ctx.obj
    try:
        topic_path = services.create_topic(knife, name)
    except AlreadyExists:
        fail(constants.MESSAGE_TOPIC_IS_ALREADY_EXISTS)
    if output == OutputFormat.JSON:
        print_json({"name": topic_path, "status": "created"})
        return
    print_success(constants.MESSAGE_TOPIC_CREATED.format(topic_path))


@app.command("list")
def list_topics(ctx: typer.Context, output: Output = OutputFormat.TEXT) -> None:
    """Lista os tópicos do projeto."""
    knife: KnifeContext = ctx.obj
    topics = services.list_topics(knife)
    if output == OutputFormat.JSON:
        print_json(topics)
        return
    if not topics:
        print_warning(constants.MESSAGE_NO_RESULT)
        return
    table = Table("Name")
    for topic in topics:
        table.add_row(topic["name"])
    console.print(table)


app.command("ls", hidden=True)(list_topics)


@app.command()
def delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nome do tópico."),
    output: Output = OutputFormat.TEXT,
) -> None:
    """Remove um tópico."""
    knife: KnifeContext = ctx.obj
    try:
        topic_path = services.delete_topic(knife, name)
    except NotFound:
        fail(constants.MESSAGE_TOPIC_NOT_FOUND)
    if output == OutputFormat.JSON:
        print_json({"name": topic_path, "status": "deleted"})
        return
    print_success(constants.MESSAGE_TOPIC_DELETED.format(topic_path))


app.command("rm", hidden=True)(delete)


@app.command()
def get(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nome do tópico."),
    output: Output = OutputFormat.TEXT,
) -> None:
    """Mostra os detalhes de um tópico."""
    knife: KnifeContext = ctx.obj
    try:
        topic = services.get_topic(knife, name)
    except NotFound:
        fail(constants.MESSAGE_TOPIC_NOT_FOUND)
    if output == OutputFormat.JSON:
        print_json(topic)
        return
    rich_print({"topic_name": topic["name"]})
