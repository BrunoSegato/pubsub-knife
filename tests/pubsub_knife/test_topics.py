from contextlib import suppress

import pytest
from google.api_core.exceptions import NotFound

pytestmark = [
    pytest.mark.integration,
    pytest.mark.topic,
]

def cleanup_topic(publisher_client):
    topic_path = publisher_client.topic_path("dummy-project", "test-topic-cli")
    with suppress(Exception):
        publisher_client.delete_topic(topic=topic_path)

@pytest.fixture(autouse=True)
def _cleanup(publisher_client):
    cleanup_topic(publisher_client)
    yield
    cleanup_topic(publisher_client)

class TestTopic:

    PROJECT_ID = "dummy-project"
    TEST_TOPIC = "test-topic-cli"

    def test_topic_create(self, cli_runner, cli_app, publisher_client):
        result = cli_runner.invoke(
            cli_app, ["topic", "create", "--name", self.TEST_TOPIC]
        )
        assert result.exit_code == 0
        assert "Topic successful created" in result.stdout

        topic_path = publisher_client.topic_path(self.PROJECT_ID, self.TEST_TOPIC)
        topic = publisher_client.get_topic(topic=topic_path)
        assert topic.name == topic_path

    def test_topic_list(self, cli_runner, cli_app, publisher_client):
        result = cli_runner.invoke(
            cli_app,
            ["topic", "create", "--name", self.TEST_TOPIC]
        )
        assert result.exit_code == 0

        topic_path = publisher_client.topic_path(self.PROJECT_ID, self.TEST_TOPIC)
        result = cli_runner.invoke(cli_app, ["topic", "list-topics"])
        assert result.exit_code == 0
        assert topic_path in result.stdout

    def test_topic_delete(self, cli_runner, cli_app, publisher_client):
        result = cli_runner.invoke(
            cli_app,
            ["topic", "create", "--name", self.TEST_TOPIC]
        )
        assert result.exit_code == 0

        topic_path = publisher_client.topic_path(self.PROJECT_ID, self.TEST_TOPIC)
        result = cli_runner.invoke(
            cli_app,
            ["topic", "delete", "--name", self.TEST_TOPIC]
        )
        assert result.exit_code == 0
        assert "Topic successful deleted." in result.stdout

        with pytest.raises(NotFound):
            publisher_client.get_topic(topic=topic_path)

    def test_topic_get(self, cli_runner, cli_app, publisher_client):
        result = cli_runner.invoke(
            cli_app,
            ["topic", "create", "--name", self.TEST_TOPIC]
        )
        assert result.exit_code == 0

        result = cli_runner.invoke(
            cli_app,
            ["topic", "get", "--name", self.TEST_TOPIC]
        )
        assert result.exit_code == 0
        assert "Topic Info" in result.stdout
