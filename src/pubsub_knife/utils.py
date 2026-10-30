from typing import NoReturn

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()
err_console = Console(stderr=True)


def print_error(message: str) -> None:
    err_console.print(Panel(
        f"[bold red]{message}[/bold red]", title="Error", style="red")
    )


def fail(message: str) -> NoReturn:
    print_error(message)
    raise typer.Exit(1)


def print_success(message: str) -> None:
    console.print(Panel(
        f"[bold green]{message}[/bold green]", title="Success", style="green")
    )


def print_warning(message: str) -> None:
    console.print(Panel(
        f"[bold yellow]{message}[/bold yellow]", title="Info", style="yellow")
    )
