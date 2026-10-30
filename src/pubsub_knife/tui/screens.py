from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.suggester import SuggestFromList
from textual.widgets import Button, Input, Label, Static, TextArea

Validator = Callable[[dict[str, str]], str | None]


@dataclass(frozen=True)
class Field:
    name: str
    label: str
    value: str = ""
    placeholder: str = ""
    multiline: bool = False
    suggestions: tuple[str, ...] = ()


class FormScreen(ModalScreen[dict[str, str] | None]):
    """
    Formulário genérico. Enter num campo de uma linha ou ctrl+s confirma,
    Esc cancela. Devolve os valores por nome do campo, ou None se cancelado.
    """

    DEFAULT_CSS = """
    FormScreen { align: center middle; }
    FormScreen > Vertical {
        width: 80; height: auto; padding: 1 2;
        border: round $primary; background: $surface;
    }
    FormScreen Label { margin-top: 1; }
    FormScreen TextArea { height: 8; }
    FormScreen #error { color: $error; height: auto; margin-top: 1; }
    FormScreen #buttons { height: auto; align-horizontal: right; margin-top: 1; }
    FormScreen Button { margin-left: 1; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel", "Cancelar"),
        ("ctrl+s", "submit", "Confirmar"),
    ]

    def __init__(
        self,
        title: str,
        fields: list[Field],
        validate: Validator | None = None
    ) -> None:
        super().__init__()
        self.form_title = title
        self.fields = fields
        self.validate = validate

    def compose(self) -> ComposeResult:
        with Vertical() as form:
            form.border_title = self.form_title
            for field in self.fields:
                yield Label(field.label)
                if field.multiline:
                    yield TextArea(field.value, id=field.name)
                else:
                    yield Input(
                        field.value,
                        placeholder=field.placeholder,
                        id=field.name,
                        suggester=(
                            SuggestFromList(field.suggestions, case_sensitive=False)
                            if field.suggestions else None
                        ),
                    )
            yield Static(id="error")
            with Horizontal(id="buttons"):
                yield Button("Confirmar", variant="primary", id="submit")
                yield Button("Cancelar", id="cancel")

    def values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for field in self.fields:
            selector = f"#{field.name}"
            if field.multiline:
                values[field.name] = self.query_one(selector, TextArea).text
            else:
                values[field.name] = self.query_one(selector, Input).value.strip()
        return values

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.action_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self.action_submit()
        else:
            self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_submit(self) -> None:
        values = self.values()
        error = self.validate(values) if self.validate else None
        if error:
            self.query_one("#error", Static).update(error)
            return
        self.dismiss(values)


class ConfirmScreen(ModalScreen[bool]):
    """Pergunta sim/não. y ou Enter confirma; n ou Esc cancela."""

    DEFAULT_CSS = """
    ConfirmScreen { align: center middle; }
    ConfirmScreen > Vertical {
        width: 70; height: auto; padding: 1 2;
        border: round $warning; background: $surface;
    }
    ConfirmScreen #buttons { height: auto; align-horizontal: right; margin-top: 1; }
    ConfirmScreen Button { margin-left: 1; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        ("y", "confirm", "Sim"),
        ("n,escape", "cancel", "Não"),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.message)
            with Horizontal(id="buttons"):
                yield Button("Sim (y)", variant="error", id="confirm")
                yield Button("Não (n)", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#confirm", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
