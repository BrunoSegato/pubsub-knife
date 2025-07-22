import typer
from rich import print
from rich.console import Console
from rich.table import Table


app = typer.Typer(pretty_exceptions_show_locals=False)
console = Console()

@app.command()
def create(
    name: str = typer.Option(..., help="Nome do tópico."),
    ctx: typer.Context = typer.Context
):
    settings = ctx.obj["settings"]
    publisher = ctx.obj["default_publisher_client"]
    topic_path = publisher.topic_path(settings.pubsub_project_id, name)
    publisher.create_topic(name=topic_path)
    data = {
        "topic_name": topic_path
    }
    print("Topic successful created.")
    print(data)


@app.command()
def list_topics(ctx: typer.Context = typer.Context):
    settings = ctx.obj["settings"]
    publisher = ctx.obj["default_publisher_client"]
    topics = publisher.list_topics(project=f"projects/{settings.pubsub_project_id}")
    table = Table("Name")
    for topic in topics:
        table.add_row(topic.name)
    console.print(table)


@app.command()
def delete(
    name: str = typer.Option(..., help="Nome do tópico."),
    ctx: typer.Context = typer.Context
):
    settings = ctx.obj["settings"]
    publisher = ctx.obj["default_publisher_client"]
    topic_path = publisher.topic_path(settings.pubsub_project_id, name)
    publisher.delete_topic(topic=topic_path)
    data = {
        "topic_name": topic_path,
    }
    print("Topic successful deleted.")
    print(data)


@app.command()
def get(
    name: str = typer.Option(..., help="Nome do tópico."),
    ctx: typer.Context = typer.Context
):
    settings = ctx.obj["settings"]
    publisher = ctx.obj["default_publisher_client"]
    topic_path = publisher.topic_path(settings.pubsub_project_id, name)
    topic = publisher.get_topic(topic=topic_path)
    print("Topic Info.")
    data = {
        "topic_name": topic.name
    }
    print(data)
