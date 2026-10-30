from contextlib import suppress

import pytest
from google.api_core.exceptions import NotFound

from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.apply,
]

TOPIC = constants.TEST_TOPIC
DLQ_TOPIC = f"{constants.TEST_TOPIC}-dlq"
WORKER = constants.TEST_SUBSCRIPTION
PUSH = f"{constants.TEST_SUBSCRIPTION}-push"

SPEC = f"""
topics:
  {TOPIC}:
    labels:
      team: payments
    subscriptions:
      - {WORKER}
      - name: {PUSH}
        push_endpoint: http://localhost:9999/webhook
        ack_deadline: 30
        filter: 'attributes.type = "created"'
        dead_letter_topic: {DLQ_TOPIC}
        max_delivery_attempts: 7
        labels:
          kind: push
  {DLQ_TOPIC}:
"""


@pytest.fixture
def spec_file(tmp_path, publisher_client, subscriber_client):
    path = tmp_path / "pubsub.yaml"
    path.write_text(SPEC)
    yield path
    for sub in (WORKER, PUSH):
        with suppress(NotFound):
            subscriber_client.delete_subscription(
                subscription=utils.get_subscription_path(
                    subscriber_client, subscription_name=sub
                )
            )
    for topic in (TOPIC, DLQ_TOPIC):
        with suppress(NotFound):
            publisher_client.delete_topic(
                topic=utils.get_topic_path(publisher_client, topic_name=topic)
            )


def apply(cli_runner, cli_app, *args, exit_code=0) -> str:
    return utils.invoke_command(
        cli_runner=cli_runner,
        cli_app=cli_app,
        command="apply",
        command_args=list(args),
        exit_code=exit_code
    )


class TestApply:

    def test_apply_creates_resources(
        self,
        cli_runner,
        cli_app,
        spec_file,
        publisher_client,
        subscriber_client
    ):
        result = apply(cli_runner, cli_app, spec_file)
        assert result.count("created") == 4

        topic = utils.get_topic(
            publisher_client, utils.get_topic_path(publisher_client)
        )
        assert dict(topic.labels) == {"team": "payments"}

        push = utils.get_subscription(
            subscriber_client,
            utils.get_subscription_path(subscriber_client, subscription_name=PUSH)
        )
        assert push.topic == utils.get_topic_path(publisher_client)
        assert push.push_config.push_endpoint == "http://localhost:9999/webhook"
        assert push.ack_deadline_seconds == 30
        assert push.filter == 'attributes.type = "created"'
        assert push.dead_letter_policy.dead_letter_topic == utils.get_topic_path(
            publisher_client, topic_name=DLQ_TOPIC
        )
        assert push.dead_letter_policy.max_delivery_attempts == 7
        assert dict(push.labels) == {"kind": "push"}

    def test_apply_is_idempotent(self, cli_runner, cli_app, spec_file):
        apply(cli_runner, cli_app, spec_file)
        result = apply(cli_runner, cli_app, spec_file)
        assert result.count("exists") == 4
        assert "created" not in result
        assert "--recreate" in result

    def test_apply_recreate(
        self,
        cli_runner,
        cli_app,
        spec_file,
        subscriber_client
    ):
        apply(cli_runner, cli_app, spec_file)
        spec_file.write_text(SPEC.replace("ack_deadline: 30", "ack_deadline: 60"))

        result = apply(cli_runner, cli_app, spec_file, "--recreate")
        assert result.count("recreated") == 4

        push = utils.get_subscription(
            subscriber_client,
            utils.get_subscription_path(subscriber_client, subscription_name=PUSH)
        )
        assert push.ack_deadline_seconds == 60

    def test_apply_file_not_found(self, cli_runner, cli_app, tmp_path):
        result = apply(
            cli_runner, cli_app, tmp_path / "nope.yaml", exit_code=1
        )
        assert "File not found" in result

    def test_apply_invalid_file(self, cli_runner, cli_app, tmp_path):
        path = tmp_path / "pubsub.yaml"
        path.write_text("topics:\n  a:\n    subscriptions:\n      - name: s\n"
                        "        dead_letter_topic: missing\n")
        result = apply(cli_runner, cli_app, path, exit_code=1)
        assert "must be declared" in result

    def test_apply_empty_file(self, cli_runner, cli_app, tmp_path):
        path = tmp_path / "pubsub.yaml"
        path.write_text("")
        result = apply(cli_runner, cli_app, path)
        assert "No topics declared" in result

    def test_apply_filter_with_attributes(
        self,
        cli_runner,
        cli_app,
        spec_file
    ):
        spec_file.write_text(f"""
topics:
  {TOPIC}:
    subscriptions:
      - name: {WORKER}
        filter: 'attributes.type = "created"'
""")
        apply(cli_runner, cli_app, spec_file)
        for kind in ("created", "cancelled"):
            utils.invoke_command(
                cli_runner=cli_runner,
                cli_app=cli_app,
                command="pub",
                command_args=[TOPIC, f"order_{kind}", "-a", f"type={kind}"]
            )
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pull",
            command_args=[WORKER, "--ack"]
        )
        assert "order_created" in result
        assert "order_cancelled" not in result
