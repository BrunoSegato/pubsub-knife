from contextlib import suppress

from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
from google.pubsub_v1.types import pubsub
from pubsub_knife.main import app
from typer.testing import CliRunner

from tests import constants


def create_topic(cli_runner: CliRunner, cli_app=app) -> None:
    result = cli_runner.invoke(
        cli_app, ["topic", "create", "--name", constants.TEST_TOPIC]
    )
    assert result.exit_code == 0
    assert "Topic successful created" in result.stdout


def create_subscription(cli_runner: CliRunner, cli_app=app) -> None:
    result = cli_runner.invoke(
        cli_app,
        [
            "subscription",
            "create",
            "--name",
            constants.TEST_SUBSCRIPTION,
            "--topic-name",
            constants.TEST_TOPIC
        ],
    )
    assert result.exit_code == 0
    assert "Subscription successful created." in result.stdout


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
