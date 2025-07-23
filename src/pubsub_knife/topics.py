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
    name: str = typer.Option(..., help="Nome do tópico."),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    settings = ctx.obj["settings"]
    publisher = ctx.obj["default_publisher_client"]
    topic_path = publisher.topic_path(settings.pubsub_project_id, name)
    try:
        publisher.create_topic(name=topic_path)
    except AlreadyExists:
        print_error(constants.MESSAGE_TOPIC_IS_ALREADY_EXISTS)
    else:
        print_success(constants.MESSAGE_TOPIC_CREATED.format(topic_path))


@app.command()
def list_topics(ctx: typer.Context = typer.Option(..., hidden=True)) -> None:
    settings = ctx.obj["settings"]
    publisher = ctx.obj["default_publisher_client"]
    topics = publisher.list_topics(project=f"projects/{settings.pubsub_project_id}")
    table = Table("Name")
    for topic in topics:
        table.add_row(topic.name)
    if not table.row_count:
        print_warning(constants.MESSAGE_NO_RESULT)
        return
    console = Console()
    console.print(table)


@app.command()
def delete(
    name: str = typer.Option(..., help="Nome do tópico."),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    settings = ctx.obj["settings"]
    publisher = ctx.obj["default_publisher_client"]
    topic_path = publisher.topic_path(settings.pubsub_project_id, name)
    try:
        publisher.delete_topic(topic=topic_path)
    except NotFound:
        print_error(constants.MESSAGE_TOPIC_NOT_FOUND)
    else:
        print_success(constants.MESSAGE_TOPIC_DELETED.format(topic_path))


@app.command()
def get(
    name: str = typer.Option(..., help="Nome do tópico."),
    ctx: typer.Context = typer.Option(..., hidden=True)
) -> None:
    settings = ctx.obj["settings"]
    publisher = ctx.obj["default_publisher_client"]
    topic_path = publisher.topic_path(settings.pubsub_project_id, name)
    try:
        topic = publisher.get_topic(topic=topic_path)
    except NotFound:
        print_error(constants.MESSAGE_TOPIC_NOT_FOUND)
    else:
        data = {
            "topic_name": topic.name
        }
        rich_print(data)
