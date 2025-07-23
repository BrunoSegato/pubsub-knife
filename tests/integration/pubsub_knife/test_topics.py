import pytest
from google.api_core.exceptions import NotFound

from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.topic,
]

class TestTopic:
    def test_topic_create(self, cli_runner, cli_app, publisher_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)

        topic_path = utils.get_topic_path(publisher_client)
        topic = utils.get_topic(publisher_client, topic_path)
        assert topic.name == topic_path

    def test_topic_list(self, cli_runner, cli_app, publisher_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)
        topic_path = utils.get_topic_path(publisher_client)

        result = cli_runner.invoke(cli_app, ["topic", "list-topics"])
        assert result.exit_code == 0
        assert topic_path in result.stdout

    def test_topic_delete(self, cli_runner, cli_app, publisher_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)
        topic_path = utils.get_topic_path(publisher_client)

        result = cli_runner.invoke(
            cli_app,
            ["topic", "delete", "--name", constants.TEST_TOPIC]
        )
        assert result.exit_code == 0
        assert "Topic successful deleted." in result.stdout

        with pytest.raises(NotFound):
            utils.get_topic(publisher_client, topic_path)

    def test_topic_get(self, cli_runner, cli_app, publisher_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)

        result = cli_runner.invoke(
            cli_app,
            ["topic", "get", "--name", constants.TEST_TOPIC]
        )
        assert result.exit_code == 0
        assert "Topic Info" in result.stdout
