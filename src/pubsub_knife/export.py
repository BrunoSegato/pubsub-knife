from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer
import yaml

from pubsub_knife import constants, services
from pubsub_knife.providers import KnifeContext
from pubsub_knife.utils import (
    Output,
    OutputFormat,
    err_console,
    fail,
    print_json,
    print_success,
)

# ack deadline que o emulador usa quando nada é informado
DEFAULT_ACK_DEADLINE = 10
# assinaturas temporárias do pk tail e do modo ao vivo da UI
TEMPORARY_PREFIX = "pk-tail-"


@dataclass
class Export:
    spec: dict[str, Any]
    topics: int = 0
    subscriptions: int = 0
    warnings: list[str] = field(default_factory=list)


def split_path(path: str) -> tuple[str, str]:
    """
    projects/<projeto>/<tipo>/<nome> -> (projeto, nome). Assinaturas de tópicos
    removidos apontam para "_deleted-topic_", que fica sem projeto.
    """
    parts = path.split("/")
    if len(parts) != 4:
        return "", path
    return parts[1], parts[-1]


def subscription_spec(
    sub: dict[str, Any],
    name: str,
    dead_letter_topic: str | None
) -> str | dict[str, Any]:
    """Só o que difere do padrão, no mesmo formato aceito pelo pk apply."""
    spec: dict[str, Any] = {"name": name}
    if sub["push_endpoint"]:
        spec["push_endpoint"] = sub["push_endpoint"]
    if sub["ack_deadline_seconds"] != DEFAULT_ACK_DEADLINE:
        spec["ack_deadline"] = sub["ack_deadline_seconds"]
    if sub["filter"]:
        spec["filter"] = sub["filter"]
    if sub["ordering"]:
        spec["ordering"] = True
    if sub["delivery_exactly_once"]:
        spec["exactly_once"] = True
    if dead_letter_topic:
        spec["dead_letter_topic"] = dead_letter_topic
        spec["max_delivery_attempts"] = sub["max_delivery_attempts"]
    if sub["labels"]:
        spec["labels"] = sub["labels"]
    # assinatura sem configuração vira só o nome, como no exemplo do README
    return name if len(spec) == 1 else spec


def build_export(knife: KnifeContext) -> Export:
    project = knife.project_id
    topics: dict[str, dict[str, Any]] = {}
    for topic in sorted(services.list_topics(knife), key=lambda t: t["name"]):
        _, name = split_path(topic["name"])
        topics[name] = {"labels": topic["labels"]} if topic["labels"] else {}

    export = Export(spec={"project": project, "topics": topics})
    subscriptions = sorted(
        services.list_subscriptions(knife), key=lambda s: s["name"]
    )
    for sub in subscriptions:
        _, name = split_path(sub["name"])
        if name.startswith(TEMPORARY_PREFIX):
            continue
        topic_project, topic_name = split_path(sub["topic"])
        if topic_project != project or topic_name not in topics:
            export.warnings.append(
                constants.MESSAGE_EXPORT_ORPHAN.format(name, sub["topic"])
            )
            continue

        dead_letter_topic = None
        if sub["dead_letter_topic"]:
            dlq_project, dlq = split_path(sub["dead_letter_topic"])
            if dlq_project == project and dlq in topics:
                dead_letter_topic = dlq
            else:
                export.warnings.append(
                    constants.MESSAGE_EXPORT_DLQ_SKIPPED.format(
                        sub["dead_letter_topic"], name
                    )
                )

        topics[topic_name].setdefault("subscriptions", []).append(
            subscription_spec(sub, name, dead_letter_topic)
        )
        export.subscriptions += 1

    export.topics = len(topics)
    return export


class SpecDumper(yaml.SafeDumper):
    """YAML no estilo do README: listas indentadas e "nome:" em vez de null."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        super().increase_indent(flow, indentless=False)


SpecDumper.add_representer(
    type(None),
    lambda dumper, _: dumper.represent_scalar("tag:yaml.org,2002:null", ""),
)


def to_yaml(spec: dict[str, Any]) -> str:
    # tópico sem nada vira "nome:", igual ao que se escreve à mão
    topics = {name: topic or None for name, topic in spec["topics"].items()}
    return yaml.dump(
        {**spec, "topics": topics},
        Dumper=SpecDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


def export(
    ctx: typer.Context,
    file: Path | None = typer.Argument(
        None, help="Arquivo de destino. Sem ele, o YAML vai para o stdout."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Sobrescreve o arquivo se ele já existir."
    ),
    output: Output = OutputFormat.TEXT,
) -> None:
    """Gera um pubsub.yaml com os tópicos e assinaturas do emulador."""
    knife: KnifeContext = ctx.obj
    if file and file.exists() and not force:
        fail(constants.MESSAGE_EXPORT_FILE_EXISTS.format(file))

    result = build_export(knife)
    # avisos no stderr para não misturar com o YAML/JSON do stdout
    for warning in result.warnings:
        err_console.print(f"[yellow]{warning}[/yellow]", highlight=False)

    content = to_yaml(result.spec)
    if file:
        file.write_text(content)
    elif output == OutputFormat.TEXT:
        print(content, end="", flush=True)

    if output == OutputFormat.JSON:
        # JSON também é YAML válido: o pk apply aceita esta saída como arquivo
        print_json(result.spec)
    elif file:
        print_success(
            constants.MESSAGE_EXPORT_DONE.format(
                result.topics, result.subscriptions, file
            )
        )
