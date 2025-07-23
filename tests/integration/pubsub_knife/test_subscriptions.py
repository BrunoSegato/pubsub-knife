
import pytest
from google.api_core.exceptions import NotFound

from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.subscription,
]


class TestSubscription:

    def test_subscription_create(self, cli_runner, cli_app, subscriber_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)
        utils.create_subscription(cli_runner=cli_runner, cli_app=cli_app)

        subscription_path = utils.get_subscription_path(
            subscriber_client=subscriber_client,
            subscription_name=constants.TEST_SUBSCRIPTION
        )
        subscription = utils.get_subscription(
            subscriber_client=subscriber_client,
            subscription_path=subscription_path
        )
        assert subscription.name == subscription_path

    def test_subscription_list(self, cli_runner, cli_app, subscriber_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)
        utils.create_subscription(cli_runner=cli_runner, cli_app=cli_app)

        result = cli_runner.invoke(cli_app, ["subscription", "list-subscriptions"])
        assert result.exit_code == 0

    def test_subscription_delete(self, cli_runner, cli_app, subscriber_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)
        utils.create_subscription(cli_runner=cli_runner, cli_app=cli_app)

        subscription_path = utils.get_subscription_path(
            subscriber_client=subscriber_client,
            subscription_name=constants.TEST_SUBSCRIPTION
        )

        result = cli_runner.invoke(
            cli_app,
            ["subscription", "delete", "--name", constants.TEST_SUBSCRIPTION]
        )
        assert result.exit_code == 0
        assert "Subscription successful deleted." in result.stdout

        with pytest.raises(NotFound):
            utils.get_subscription(
                subscriber_client=subscriber_client,
                subscription_path=subscription_path
            )

    def test_subscription_get(self, cli_runner, cli_app, subscriber_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)
        utils.create_subscription(cli_runner=cli_runner, cli_app=cli_app)

        result = cli_runner.invoke(
            cli_app,
            ["subscription", "get", "--name", constants.TEST_SUBSCRIPTION]
        )
        assert result.exit_code == 0
        assert "Subscription Info." in result.stdout
