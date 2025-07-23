import pytest

from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.consumer,
]

class TestConsumer:

    def test_pull_without_message(self, cli_runner, cli_app, subscriber_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)
        utils.create_subscription(cli_runner=cli_runner, cli_app=cli_app)

        result = cli_runner.invoke(
            cli_app,
            [
                "consumer",
                "pull",
                "--subscription",
                constants.TEST_SUBSCRIPTION,
                "--max-messages",
                1,
                "--auto-ack"
            ]
        )
        assert result.exit_code == 0
        assert "Nenhuma mensagem encontrada." in result.stdout
