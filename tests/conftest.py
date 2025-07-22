import pytest
from google.cloud.pubsub_v1 import PublisherClient
from pubsub_knife.main import app
from typer.testing import CliRunner


@pytest.fixture()
def cli_runner():
    return CliRunner()

@pytest.fixture()
def cli_app():
    return app

@pytest.fixture()
def publisher_client():
    return PublisherClient()
