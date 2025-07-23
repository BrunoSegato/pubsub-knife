from google.cloud.pubsub_v1.futures import Future
from rich import print as rich_print
from rich.console import Console
from rich.panel import Panel

from src import constants


def callback(future: Future) -> None:
    try:
        msg_id = future.result()
        rich_print(constants.MESSAGE_PUBLISHED_WITH_CALLBACK.format(msg_id))
    except Exception as e:
        rich_print(constants.MESSAGE_PUBLISHED_ERROR_WITH_CALLBACK.format(e))

def print_error(message: str) -> None:
    console = Console()
    console.print(Panel(
        f"[bold red]{message}[/bold red]", title="Error", style="red")
    )

def print_success(message: str) -> None:
    console = Console()
    console.print(Panel(
        f"[bold green]{message}[/bold green]", title="Success", style="green")
    )

def print_warning(message: str) -> None:
    console = Console()
    console.print(Panel(
        f"[bold yellow]{message}[/bold yellow]", title="Info", style="yellow")
    )
