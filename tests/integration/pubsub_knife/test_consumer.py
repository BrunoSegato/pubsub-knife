import pytest

from src import constants as src_constants
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
        assert src_constants.MESSAGE_NO_RESULT in result
