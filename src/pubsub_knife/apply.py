from contextlib import suppress
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

import typer
import yaml
from google.api_core.exceptions import AlreadyExists, GoogleAPICallError, NotFound
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from rich.table import Table

from pubsub_knife import constants
from pubsub_knife.providers import KnifeContext
from pubsub_knife.utils import (
    Output,
    OutputFormat,
    console,
    fail,
    print_json,
    print_warning,
)


class SubscriptionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    push_endpoint: str | None = None
    ack_deadline: int | None = Field(default=None, ge=10, le=600)
    filter_: str | None = Field(default=None, alias="filter")
    ordering: bool = False
    exactly_once: bool = False
    dead_letter_topic: str | None = None
    max_delivery_attempts: int = Field(default=5, ge=5, le=100)
    labels: dict[str, str] = Field(default_factory=dict)


class TopicSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subscriptions: list[SubscriptionSpec] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        if data is None:
            return {}
        if isinstance(data, dict) and isinstance(data.get("subscriptions"), list):
            data["subscriptions"] = [
                {"name": sub} if isinstance(sub, str) else sub
                for sub in data["subscriptions"]
            ]
        return data


class PubSubSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str | None = None
    topics: dict[str, TopicSpec] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("topics"), dict):
            data["topics"] = {k: v or {} for k, v in data["topics"].items()}
        return data

    @model_validator(mode="after")
    def check_references(self) -> Self:
        seen: set[str] = set()
        for topic_name, topic in self.topics.items():
            for sub in topic.subscriptions:
                if sub.name in seen:
                    raise ValueError(f"duplicated subscription '{sub.name}'")
                seen.add(sub.name)
                dlq = sub.dead_letter_topic
                if dlq and dlq not in self.topics:
                    raise ValueError(
                        f"dead_letter_topic '{dlq}' of subscription '{sub.name}' "
                        f"(topic '{topic_name}') must be declared in topics"
                    )
        return self


class Status(StrEnum):
    CREATED = "created"
    EXISTS = "exists"
    RECREATED = "recreated"
    FAILED = "failed"


STATUS_STYLE = {
    Status.CREATED: "green",
    Status.RECREATED: "green",
    Status.EXISTS: "yellow",
    Status.FAILED: "bold red",
}


def load_spec(path: Path) -> PubSubSpec:
    if not path.is_file():
        fail(constants.MESSAGE_APPLY_FILE_NOT_FOUND.format(path))
    try:
        return PubSubSpec.model_validate(yaml.safe_load(path.read_text()) or {})
    except yaml.YAMLError as e:
        fail(constants.MESSAGE_APPLY_INVALID_FILE.format(path, e))
    except ValidationError as e:
        fail(constants.MESSAGE_APPLY_INVALID_FILE.format(path, e))


def build_subscription_request(
    knife: KnifeContext,
    topic: str,
    spec: SubscriptionSpec
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "name": knife.subscription_path(spec.name),
        "topic": knife.topic_path(topic),
        "labels": spec.labels,
        "enable_message_ordering": spec.ordering,
        "enable_exactly_once_delivery": spec.exactly_once,
    }
    if spec.push_endpoint:
        request["push_config"] = {"push_endpoint": spec.push_endpoint}
    if spec.ack_deadline:
        request["ack_deadline_seconds"] = spec.ack_deadline
    if spec.filter_:
        request["filter"] = spec.filter_
    if spec.dead_letter_topic:
        request["dead_letter_policy"] = {
            "dead_letter_topic": knife.topic_path(spec.dead_letter_topic),
            "max_delivery_attempts": spec.max_delivery_attempts,
        }
    return request


def delete_declared(knife: KnifeContext, spec: PubSubSpec) -> set[str]:
    """Remove as assinaturas e tópicos do arquivo. Retorna os paths que existiam."""
    deleted: set[str] = set()
    for topic in spec.topics.values():
        for sub in topic.subscriptions:
            path = knife.subscription_path(sub.name)
            with suppress(NotFound):
                knife.subscriber.delete_subscription(subscription=path)
                deleted.add(path)
    for topic_name in spec.topics:
        path = knife.topic_path(topic_name)
        with suppress(NotFound):
            knife.publisher.delete_topic(topic=path)
            deleted.add(path)
    return deleted


def create(
    path: str,
    create_fn: Any,
    request: dict[str, Any],
    deleted: set[str]
) -> tuple[Status, str]:
    try:
        create_fn(request=request)
    except AlreadyExists:
        return Status.EXISTS, ""
    except GoogleAPICallError as e:
        return Status.FAILED, e.message or str(e)
    return (Status.RECREATED if path in deleted else Status.CREATED), ""


def apply(
    ctx: typer.Context,
    file: Path = typer.Argument(
        Path("pubsub.yaml"), help="Arquivo com os tópicos e assinaturas."
    ),
    recreate: bool = typer.Option(
        False,
        "--recreate",
        help="Remove e recria os recursos declarados (para aplicar mudanças).",
    ),
    output: Output = OutputFormat.TEXT,
) -> None:
    """Cria os tópicos e assinaturas declarados em um arquivo YAML."""
    knife: KnifeContext = ctx.obj
    spec = load_spec(file)
    if spec.project and not knife.project_overridden:
        knife.settings.pubsub_project_id = spec.project

    as_json = output == OutputFormat.JSON
    if not spec.topics:
        if as_json:
            print_json({"project": knife.project_id, "resources": []})
            return
        print_warning(constants.MESSAGE_APPLY_EMPTY.format(file))
        return

    deleted = delete_declared(knife, spec) if recreate else set()
    resources: list[dict[str, Any]] = []

    def report(kind: str, name: str, status: Status, detail: str) -> None:
        resources.append(
            {"kind": kind, "name": name, "status": status, "detail": detail}
        )

    for topic_name, topic in spec.topics.items():
        path = knife.topic_path(topic_name)
        report(
            "topic", topic_name,
            *create(
                path,
                knife.publisher.create_topic,
                {"name": path, "labels": topic.labels},
                deleted
            )
        )

    for topic_name, topic in spec.topics.items():
        for sub in topic.subscriptions:
            report(
                "subscription", sub.name,
                *create(
                    knife.subscription_path(sub.name),
                    knife.subscriber.create_subscription,
                    build_subscription_request(knife, topic_name, sub),
                    deleted
                )
            )

    if as_json:
        print_json({"project": knife.project_id, "resources": resources})
    else:
        print_table(knife.project_id, resources)
    if any(r["status"] == Status.FAILED for r in resources):
        raise typer.Exit(1)


def print_table(project_id: str, resources: list[dict[str, Any]]) -> None:
    table = Table("Resource", "Name", "Status", "Detail")
    for r in resources:
        style = STATUS_STYLE[r["status"]]
        table.add_row(
            r["kind"], r["name"], f"[{style}]{r['status']}[/{style}]", r["detail"]
        )
    console.print(f"Project: [bold]{project_id}[/bold]")
    console.print(table)
    if any(r["status"] == Status.EXISTS for r in resources):
        console.print(constants.MESSAGE_APPLY_EXISTS_HINT)
