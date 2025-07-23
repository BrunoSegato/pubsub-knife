import pytest
from google.api_core.exceptions import NotFound

from src import constants as src_constants
from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.subscription,
]


class TestSubscription:

    def test_create_subscription(
        self,
        subscriber_client,
        ready_subscription
    ):
        _, subscription_path = ready_subscription

        subscription = utils.get_subscription(
            subscriber_client=subscriber_client,
            subscription_path=subscription_path
        )
        assert subscription.name == subscription_path

    def test_create_subscription_already_exists(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription

        utils.create_subscription(
            cli_runner=cli_runner,
            cli_app=cli_app,
            expected_message=src_constants.MESSAGE_SUBSCRIPTION_IS_ALREADY_EXISTS
        )

    def test_list_with_subscriptions(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription
        utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="subscription",
            command_args=["list-subscriptions"]
        )

    def test_list_without_subscriptions(
        self,
        cli_runner,
        cli_app
    ):
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="subscription",
            command_args=["list-subscriptions"]
        )
        assert src_constants.MESSAGE_NO_RESULT in result

    def test_delete_exists_subscription(
        self,
        cli_runner,
        cli_app,
        subscriber_client,
        ready_subscription
    ):
        _, subscription_path = ready_subscription
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="subscription",
            command_args=["delete", "--name", constants.TEST_SUBSCRIPTION]
        )
        expected_message = src_constants.MESSAGE_SUBSCRIPTION_DELETED.format(
            subscription_path
        )
        clean_output = utils.extract_panel_content(result)
        assert expected_message in clean_output

        with pytest.raises(NotFound):
            utils.get_subscription(
                subscriber_client=subscriber_client,
                subscription_path=subscription_path
            )

    def test_delete_unexists_subscription(
        self,
        cli_runner,
        cli_app
    ):
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="subscription",
            command_args=["delete", "--name", constants.TEST_SUBSCRIPTION]
        )
        assert src_constants.MESSAGE_SUBSCRIPTION_NOT_FOUND in result

    def test_get_exists_subscription(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _, subscription_path = ready_subscription
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="subscription",
            command_args=["get", "--name", constants.TEST_SUBSCRIPTION]
        )
        assert subscription_path in result

    def test_get_unexists_subscription(
        self,
        cli_runner,
        cli_app,
    ):
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="subscription",
            command_args=["get", "--name", constants.TEST_SUBSCRIPTION]
        )
        assert src_constants.MESSAGE_SUBSCRIPTION_NOT_FOUND in result
