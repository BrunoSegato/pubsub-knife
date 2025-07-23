from contextlib import suppress

import typer
from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
from google.pubsub_v1.types import pubsub
from typer.testing import CliRunner

from src import constants as src_constants
from tests import constants


def create_topic(
    cli_runner: CliRunner,
    cli_app: typer.Typer,
    expected_message: str
) -> None:
    result = cli_runner.invoke(
        cli_app, ["topic", "create", "--name", constants.TEST_TOPIC]
    )
    clean_output = extract_panel_content(result.stdout)
    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert expected_message in clean_output

def create_subscription(
    cli_runner: CliRunner,
    cli_app: typer.Typer,
    expected_message: str
) -> None:
    result = cli_runner.invoke(
        cli_app,
        [
            "subscription",
            "create",
            "--name",
            constants.TEST_SUBSCRIPTION,
            "--topic-name",
            constants.TEST_TOPIC
        ]
    )
    clean_output = extract_panel_content(result.stdout)
    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert expected_message in clean_output

def cleanup_topic_and_subscription(
    publisher_client: PublisherClient,
    subscriber_client: SubscriberClient
):
    topic_path = publisher_client.topic_path(
        constants.PROJECT_ID, constants.TEST_TOPIC
    )
    subscription_path = subscriber_client.subscription_path(
        constants.PROJECT_ID, constants.TEST_SUBSCRIPTION
    )
    with suppress(Exception):
        subscriber_client.delete_subscription(subscription=subscription_path)
    with suppress(Exception):
        publisher_client.delete_topic(topic=topic_path)

def get_topic_path(
    publisher_client: PublisherClient,
    project_id: str | None = None,
    topic_name: str | None = None
) -> str:
    if not project_id:
        project_id = constants.PROJECT_ID
    if not topic_name:
        topic_name = constants.TEST_TOPIC
    return publisher_client.topic_path(project_id, topic_name)

def get_topic(publisher_client: PublisherClient, topic_path: str) -> pubsub.Topic:
    return publisher_client.get_topic(topic=topic_path)

def get_subscription_path(
    subscriber_client: SubscriberClient,
    project_id: str | None = None,
    subscription_name: str | None = None
) -> str:
    if not project_id:
        project_id = constants.PROJECT_ID
    if not subscription_name:
        subscription_name = constants.TEST_SUBSCRIPTION
    return subscriber_client.subscription_path(project_id, subscription_name)

def get_subscription(
    subscriber_client: SubscriberClient,
    subscription_path: str
) -> pubsub.Subscription:
    return subscriber_client.get_subscription(subscription=subscription_path)

def extract_panel_content(output: str) -> str:
    lines = output.splitlines()
    content_lines = [line.strip("│ ") for line in lines if line.strip().startswith("│")]
    return " ".join(content_lines)

def setup_topic_and_subscription(
    cli_runner,
    cli_app,
    publisher_client,
    subscriber_client
):
    topic_path = get_topic_path(publisher_client)
    subscription_path = get_subscription_path(subscriber_client)

    create_topic(
        cli_runner=cli_runner,
        cli_app=cli_app,
        expected_message=src_constants.MESSAGE_TOPIC_CREATED.format(topic_path)
    )
    create_subscription(
        cli_runner=cli_runner,
        cli_app=cli_app,
        expected_message=src_constants.MESSAGE_SUBSCRIPTION_CREATED.format(subscription_path)
    )
    return topic_path, subscription_path

def setup_topic(cli_runner, cli_app, publisher_client):
    topic_path = get_topic_path(publisher_client)

    create_topic(
        cli_runner=cli_runner,
        cli_app=cli_app,
        expected_message=src_constants.MESSAGE_TOPIC_CREATED.format(topic_path)
    )

    return topic_path

def invoke_command(cli_runner, cli_app, command, command_args: list[str]) -> str:
    result = cli_runner.invoke(cli_app, [command, *command_args])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    return result.stdout
