from typing import NoReturn

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

console = Console()
err_console = Console(stderr=True)


def _panel(message: str, color: str, title: str) -> Panel:
    return Panel(
        f"[bold {color}]{escape(message)}[/bold {color}]", title=title, style=color
    )


def print_error(message: str) -> None:
    err_console.print(_panel(message, "red", "Error"))


def fail(message: str) -> NoReturn:
    print_error(message)
    raise typer.Exit(1)


def print_success(message: str) -> None:
    console.print(_panel(message, "green", "Success"))


def print_warning(message: str) -> None:
    console.print(_panel(message, "yellow", "Info"))
