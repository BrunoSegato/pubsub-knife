import pytest

from pubsub_knife import constants as src_constants
from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.consumer,
]

class TestConsumer:

    def test_pull_without_message(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pull",
            command_args=[constants.TEST_SUBSCRIPTION, "-n", 1, "--ack"]
        )
        assert src_constants.MESSAGE_NO_RESULT in result

    def test_pull_unexists_subscription(
        self,
        cli_runner,
        cli_app
    ):
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pull",
            command_args=[constants.TEST_SUBSCRIPTION],
            exit_code=1
        )
        assert src_constants.MESSAGE_SUBSCRIPTION_NOT_FOUND in result

    def test_pull_with_ack_removes_message(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription
        utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pub",
            command_args=[constants.TEST_TOPIC, "ack_me"]
        )
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pull",
            command_args=[constants.TEST_SUBSCRIPTION, "--ack"]
        )
        assert "ack_me" in result
        assert src_constants.MESSAGE_CONSUMER_ALL_ACK in result

        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pull",
            command_args=[constants.TEST_SUBSCRIPTION]
        )
        assert src_constants.MESSAGE_NO_RESULT in result
