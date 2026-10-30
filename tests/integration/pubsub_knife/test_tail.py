import json
import threading

import pytest

from pubsub_knife import constants as src_constants
from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.tail,
]


def publish(publisher_client, topic_path, *messages: bytes) -> None:
    for message in messages:
        publisher_client.publish(topic_path, message).result()


def tail(cli_runner, cli_app, *args, exit_code=0) -> str:
    return utils.invoke_command(
        cli_runner=cli_runner,
        cli_app=cli_app,
        command="tail",
        command_args=list(args),
        exit_code=exit_code
    )


def pull(cli_runner, cli_app) -> str:
    return utils.invoke_command(
        cli_runner=cli_runner,
        cli_app=cli_app,
        command="pull",
        command_args=[constants.TEST_SUBSCRIPTION, "--ack"]
    )


class TestTail:

    def test_tail_without_ack_returns_messages(
        self,
        cli_runner,
        cli_app,
        publisher_client,
        ready_subscription
    ):
        topic_path, _ = ready_subscription
        publish(publisher_client, topic_path, b'{"id": 1}', b"plain")

        result = tail(
            cli_runner, cli_app,
            constants.TEST_SUBSCRIPTION, "-n", 2, "--timeout", 10
        )
        assert '"id": 1' in result
        assert "plain" in result
        assert "Stopped after 2 message(s)" in result

        result = pull(cli_runner, cli_app)
        assert '"id": 1' in result
        assert "plain" in result

    def test_tail_with_ack_consumes_messages(
        self,
        cli_runner,
        cli_app,
        publisher_client,
        ready_subscription
    ):
        topic_path, _ = ready_subscription
        publish(publisher_client, topic_path, b"consume_me")

        result = tail(
            cli_runner, cli_app,
            constants.TEST_SUBSCRIPTION, "-n", 1, "--timeout", 10, "--ack"
        )
        assert "consume_me" in result
        assert src_constants.MESSAGE_NO_RESULT in pull(cli_runner, cli_app)

    def test_tail_stops_on_timeout(self, cli_runner, cli_app, ready_subscription):
        _ = ready_subscription
        result = tail(
            cli_runner, cli_app, constants.TEST_SUBSCRIPTION, "--timeout", 1
        )
        assert "Stopped after 0 message(s)" in result

    def test_tail_jsonl(
        self,
        cli_runner,
        cli_app,
        publisher_client,
        ready_subscription
    ):
        topic_path, _ = ready_subscription
        publish(publisher_client, topic_path, b"line")

        result = tail(
            cli_runner, cli_app,
            constants.TEST_SUBSCRIPTION, "-n", 1, "--timeout", 10, "--jsonl"
        )
        lines = [line for line in result.splitlines() if line.startswith("{")]
        assert len(lines) == 1
        assert json.loads(lines[0])["data"] == "line"

    def test_tail_topic_uses_temporary_subscription(
        self,
        cli_runner,
        cli_app,
        publisher_client,
        subscriber_client,
        ready_topic
    ):
        topic_path = ready_topic
        timer = threading.Timer(
            1.5, publish, args=(publisher_client, topic_path, b"from_topic")
        )
        timer.start()

        result = tail(
            cli_runner, cli_app,
            "--topic", constants.TEST_TOPIC, "-n", 1, "--timeout", 10
        )
        timer.join()
        assert "from_topic" in result

        subscriptions = subscriber_client.list_subscriptions(
            project=f"projects/{constants.PROJECT_ID}"
        )
        assert not [s for s in subscriptions if "pk-tail-" in s.name]

    def test_tail_unexists_subscription(self, cli_runner, cli_app):
        result = tail(cli_runner, cli_app, constants.TEST_SUBSCRIPTION, exit_code=1)
        assert src_constants.MESSAGE_SUBSCRIPTION_NOT_FOUND in result

    def test_tail_unexists_topic(self, cli_runner, cli_app):
        result = tail(
            cli_runner, cli_app, "--topic", constants.TEST_TOPIC, exit_code=1
        )
        assert src_constants.MESSAGE_TOPIC_NOT_FOUND in result

    @pytest.mark.parametrize(
        "args", [[], [constants.TEST_SUBSCRIPTION, "--topic", constants.TEST_TOPIC]]
    )
    def test_tail_requires_exactly_one_target(self, cli_runner, cli_app, args):
        result = tail(cli_runner, cli_app, *args, exit_code=1)
        assert "Provide a subscription or --topic" in result
