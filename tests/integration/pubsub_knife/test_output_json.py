import json

import pytest

from pubsub_knife import constants as src_constants
from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
]


def run_json(cli_runner, cli_app, *args, exit_code=0):
    result = cli_runner.invoke(cli_app, [*map(str, args), "-o", "json"])
    assert result.exit_code == exit_code, f"Unexpected exit: {result.output}"
    # o stdout precisa ser só o JSON, sem mensagens de progresso
    return json.loads(result.stdout)


class TestOutputJson:

    def test_topic_create_get_list_delete(self, cli_runner, cli_app, publisher_client):
        topic_path = utils.get_topic_path(publisher_client)

        created = run_json(cli_runner, cli_app, "topic", "create", constants.TEST_TOPIC)
        assert created == {"name": topic_path, "status": "created"}

        topic = run_json(cli_runner, cli_app, "topic", "get", constants.TEST_TOPIC)
        assert topic == {"name": topic_path, "labels": {}}

        topics = run_json(cli_runner, cli_app, "topic", "list")
        assert topics == [{"name": topic_path, "labels": {}}]

        deleted = run_json(cli_runner, cli_app, "topic", "delete", constants.TEST_TOPIC)
        assert deleted == {"name": topic_path, "status": "deleted"}

    def test_empty_list_is_empty_array(self, cli_runner, cli_app):
        assert run_json(cli_runner, cli_app, "topic", "list") == []
        assert run_json(cli_runner, cli_app, "sub", "list") == []

    def test_subscription_get_and_list(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        topic_path, subscription_path = ready_subscription

        subscription = run_json(
            cli_runner, cli_app, "sub", "get", constants.TEST_SUBSCRIPTION
        )
        assert subscription["name"] == subscription_path
        assert subscription["topic"] == topic_path
        assert subscription["push_endpoint"] is None
        assert isinstance(subscription["retention_seconds"], int)

        subscriptions = run_json(cli_runner, cli_app, "sub", "list")
        assert [s["name"] for s in subscriptions] == [subscription_path]

    def test_publish_and_pull(self, cli_runner, cli_app, ready_subscription):
        topic_path, _ = ready_subscription

        published = run_json(
            cli_runner, cli_app,
            "pub", constants.TEST_TOPIC, '{"id": 1}', "-a", "type=created",
            "--repeat", 2
        )
        assert published["topic"] == topic_path
        assert len(published["message_ids"]) == 2
        assert published["errors"] == []

        messages = run_json(
            cli_runner, cli_app, "pull", constants.TEST_SUBSCRIPTION, "--ack"
        )
        assert sorted(m["id"] for m in messages) == sorted(published["message_ids"])
        assert all(m["data"] == '{"id": 1}' for m in messages)
        assert all(m["attributes"] == {"type": "created"} for m in messages)

        assert run_json(cli_runner, cli_app, "pull", constants.TEST_SUBSCRIPTION) == []

    def test_apply(self, cli_runner, cli_app, tmp_path):
        spec = tmp_path / "pubsub.yaml"
        spec.write_text(
            f"topics:\n  {constants.TEST_TOPIC}:\n"
            f"    subscriptions: [{constants.TEST_SUBSCRIPTION}]\n"
        )

        result = run_json(cli_runner, cli_app, "apply", spec)
        assert result == {
            "project": utils.current_project(),
            "resources": [
                {"kind": "topic", "name": constants.TEST_TOPIC,
                 "status": "created", "detail": ""},
                {"kind": "subscription", "name": constants.TEST_SUBSCRIPTION,
                 "status": "created", "detail": ""},
            ],
        }

        again = run_json(cli_runner, cli_app, "apply", spec)
        assert {r["status"] for r in again["resources"]} == {"exists"}

    def test_tail_emits_jsonl(
        self,
        cli_runner,
        cli_app,
        publisher_client,
        ready_subscription
    ):
        topic_path, _ = ready_subscription
        publisher_client.publish(topic_path, b"hello").result()

        result = cli_runner.invoke(
            cli_app,
            ["tail", constants.TEST_SUBSCRIPTION, "-o", "json", "-n", "1",
             "--timeout", "10"]
        )
        assert result.exit_code == 0, result.output
        lines = result.stdout.splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["data"] == "hello"

    def test_env_var_sets_output(self, cli_runner, cli_app):
        result = cli_runner.invoke(
            cli_app, ["topic", "list"], env={"PK_OUTPUT": "json"}
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout) == []

    def test_error_keeps_stdout_clean(self, cli_runner, cli_app):
        result = cli_runner.invoke(cli_app, ["topic", "get", "missing", "-o", "json"])
        assert result.exit_code == 1
        assert result.stdout == ""
        assert src_constants.MESSAGE_TOPIC_NOT_FOUND in result.stderr
