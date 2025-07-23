import pytest

from src import constants as src_constants
from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.publisher,
]

class TestPublisher:

    def test_publisher_publish_sync(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        topic_path, _ = ready_subscription
        expected_message = "test_message"

        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="publisher",
            command_args=[
                "sync",
                "--topic",
                constants.TEST_TOPIC,
                "--message",
                expected_message
            ]
        )
        assert src_constants.MESSAGE_PUBLISH_SYNC.format(topic_path) in result
        assert "Message publish with ID" in result

        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="consumer",
            command_args=[
                "pull",
                "--subscription",
                constants.TEST_SUBSCRIPTION,
                "--max-messages",
                1,
                "--auto-ack"
            ]
        )
        assert src_constants.MESSAGE_NO_RESULT not in result
        assert expected_message in result

    def test_publisher_with_callback(
        self,
        cli_runner,
        cli_app,
        publisher_client,
        subscriber_client,
        ready_subscription,
    ):
        topic_path, _ = ready_subscription
        expected_message = "callback_test_message"

        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="publisher",
            command_args=[
                "with-callback",
                "--topic",
                constants.TEST_TOPIC,
                "--message",
                expected_message
            ]
        )
        assert src_constants.MESSAGE_PUBLISH_CALLBACK.format(topic_path) in result
        assert src_constants.MESSAGE_PUBLISH_WAIT_TO_CALLBACK in result
        assert src_constants.MESSAGE_PUBLISHED_WITH_CALLBACK.format("") in result

        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="consumer",
            command_args=[
                "pull",
                "--subscription",
                constants.TEST_SUBSCRIPTION,
                "--max-messages",
                1,
                "--auto-ack"
            ]
        )

        assert src_constants.MESSAGE_NO_RESULT not in result
        assert expected_message in result
