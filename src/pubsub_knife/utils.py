import json
from enum import StrEnum
from typing import Annotated, Any, NoReturn

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


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


Output = Annotated[
    OutputFormat,
    typer.Option(
        "--output", "-o", envvar="PK_OUTPUT",
        help="Formato da saída. json vai para o stdout, pronto para jq.",
    ),
]


def print_json(data: Any) -> None:
    # print direto (sem rich) para não colorir nem quebrar o JSON
    print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)
