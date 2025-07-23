import pytest
from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
from pubsub_knife.main import app
from typer.testing import CliRunner

from tests import utils


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()

@pytest.fixture()
def cli_app():
    return app

@pytest.fixture()
def publisher_client() -> PublisherClient:
    return PublisherClient()

@pytest.fixture()
def subscriber_client() -> SubscriberClient:
    return SubscriberClient()

@pytest.fixture(autouse=True)
def _cleanup(publisher_client, subscriber_client):
    utils.cleanup_topic_and_subscription(publisher_client, subscriber_client)
    yield
    utils.cleanup_topic_and_subscription(publisher_client, subscriber_client)
