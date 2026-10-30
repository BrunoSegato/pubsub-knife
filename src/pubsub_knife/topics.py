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
    name: str = typer.Argument(..., help="Nome do tópico."),
) -> None:
    """Cria um tópico."""
    knife: KnifeContext = ctx.obj
    topic_path = knife.topic_path(name)
    try:
        knife.publisher.create_topic(name=topic_path)
    except AlreadyExists:
        fail(constants.MESSAGE_TOPIC_IS_ALREADY_EXISTS)
    print_success(constants.MESSAGE_TOPIC_CREATED.format(topic_path))


@app.command("list")
def list_topics(ctx: typer.Context) -> None:
    """Lista os tópicos do projeto."""
    knife: KnifeContext = ctx.obj
    topics = knife.publisher.list_topics(project=knife.project_path)
    table = Table("Name")
    for topic in topics:
        table.add_row(topic.name)
    if not table.row_count:
        print_warning(constants.MESSAGE_NO_RESULT)
        return
    console.print(table)


app.command("ls", hidden=True)(list_topics)


@app.command()
def delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nome do tópico."),
) -> None:
    """Remove um tópico."""
    knife: KnifeContext = ctx.obj
    topic_path = knife.topic_path(name)
    try:
        knife.publisher.delete_topic(topic=topic_path)
    except NotFound:
        fail(constants.MESSAGE_TOPIC_NOT_FOUND)
    print_success(constants.MESSAGE_TOPIC_DELETED.format(topic_path))


app.command("rm", hidden=True)(delete)


@app.command()
def get(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nome do tópico."),
) -> None:
    """Mostra os detalhes de um tópico."""
    knife: KnifeContext = ctx.obj
    try:
        topic = knife.publisher.get_topic(topic=knife.topic_path(name))
    except NotFound:
        fail(constants.MESSAGE_TOPIC_NOT_FOUND)
    rich_print({"topic_name": topic.name})
