import uuid

import pytest
from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
from typer.testing import CliRunner

from pubsub_knife.main import app
from tests import constants, utils


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()

@pytest.fixture
def cli_app():
    return app

@pytest.fixture
def publisher_client() -> PublisherClient:
    return PublisherClient()

@pytest.fixture
def subscriber_client() -> SubscriberClient:
    return SubscriberClient()

@pytest.fixture(autouse=True)
def _isolated_project(request, monkeypatch):
    """
    Cada teste de integração roda em um projeto próprio no emulador: não enxerga
    recursos de outros testes nem os criados à mão em outros projetos.
    """
    if request.node.get_closest_marker("integration") is None:
        yield
        return
    publisher_client = request.getfixturevalue("publisher_client")
    subscriber_client = request.getfixturevalue("subscriber_client")
    project_id = f"{constants.PROJECT_PREFIX}-{uuid.uuid4().hex[:12]}"
    monkeypatch.setenv("PUBSUB_PROJECT_ID", project_id)
    yield project_id
    utils.cleanup_project(publisher_client, subscriber_client, project_id)

@pytest.fixture
def ready_subscription(cli_runner, cli_app, subscriber_client, publisher_client):
    return utils.setup_topic_and_subscription(
        cli_runner=cli_runner,
        cli_app=cli_app,
        subscriber_client=subscriber_client,
        publisher_client=publisher_client,
    )

@pytest.fixture
def ready_topic(cli_runner, cli_app, publisher_client):
    return utils.setup_topic(
        cli_runner=cli_runner,
        cli_app=cli_app,
        publisher_client=publisher_client,
    )
