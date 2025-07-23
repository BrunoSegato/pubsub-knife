import pytest
from google.api_core.exceptions import NotFound

from src import constants as src_constants
from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.topic,
]

class TestTopic:
    def test_create_topic(
        self,
        cli_runner,
        cli_app,
        publisher_client,
        ready_topic
    ):
        topic_path = ready_topic

        topic = utils.get_topic(publisher_client, topic_path)
        assert topic.name == topic_path

    def test_create_topic_already_exists(
        self,
        cli_runner,
        cli_app,
        ready_topic
    ):
        _ = ready_topic

        utils.create_topic(
            cli_runner=cli_runner,
            cli_app=cli_app,
            expected_message=src_constants.MESSAGE_TOPIC_IS_ALREADY_EXISTS
        )

    def test_list_with_topics(
        self,
        cli_runner,
        cli_app,
        ready_topic
    ):
        _ = ready_topic
        utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="topic",
            command_args=["list-topics"]
        )

    def test_list_without_topics(
        self,
        cli_runner,
        cli_app
    ):
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="topic",
            command_args=["list-topics"]
        )
        assert src_constants.MESSAGE_NO_RESULT in result

    def test_delete_exists_topic(
        self,
        cli_runner,
        cli_app,
        publisher_client,
        ready_topic
    ):
        topic_path = ready_topic
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="topic",
            command_args=["delete", "--name", constants.TEST_TOPIC]
        )
        expected_message = src_constants.MESSAGE_TOPIC_DELETED.format(topic_path)
        assert expected_message in result

        with pytest.raises(NotFound):
            utils.get_topic(publisher_client, topic_path)

    def test_delete_unexists_topic(
        self,
        cli_runner,
        cli_app
    ):
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="topic",
            command_args=["delete", "--name", constants.TEST_TOPIC]
        )
        assert src_constants.MESSAGE_TOPIC_NOT_FOUND in result

    def test_get_exists_topic(
        self,
        cli_runner,
        cli_app,
        ready_topic
    ):
        topic_path = ready_topic
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="topic",
            command_args=["get", "--name", constants.TEST_TOPIC]
        )
        assert topic_path in result

    def test_get_unexists_topic(
        self,
        cli_runner,
        cli_app
    ):
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="topic",
            command_args=["get", "--name", constants.TEST_TOPIC]
        )
        assert src_constants.MESSAGE_TOPIC_NOT_FOUND in result
