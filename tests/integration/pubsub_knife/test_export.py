import json
import uuid

import pytest
import yaml

from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
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
        ordering: true
        dead_letter_topic: {DLQ_TOPIC}
        max_delivery_attempts: 7
        labels:
          kind: push
  {DLQ_TOPIC}:
"""


def run(cli_runner, cli_app, *args, exit_code=0):
    result = cli_runner.invoke(cli_app, list(map(str, args)))
    assert result.exit_code == exit_code, f"Unexpected exit: {result.output}"
    return result


@pytest.fixture
def applied(cli_runner, cli_app, tmp_path):
    spec = tmp_path / "pubsub.yaml"
    spec.write_text(SPEC)
    run(cli_runner, cli_app, "apply", spec)


class TestExport:

    def test_exports_only_what_differs_from_defaults(
        self,
        cli_runner,
        cli_app,
        applied
    ):
        exported = yaml.safe_load(run(cli_runner, cli_app, "export").stdout)
        assert exported == {
            "project": utils.current_project(),
            "topics": {
                TOPIC: {
                    "labels": {"team": "payments"},
                    "subscriptions": [
                        WORKER,
                        {
                            "name": PUSH,
                            "push_endpoint": "http://localhost:9999/webhook",
                            "ack_deadline": 30,
                            "filter": 'attributes.type = "created"',
                            "ordering": True,
                            "dead_letter_topic": DLQ_TOPIC,
                            "max_delivery_attempts": 7,
                            "labels": {"kind": "push"},
                        },
                    ],
                },
                DLQ_TOPIC: None,
            },
        }

    def test_round_trip_into_another_project(
        self,
        cli_runner,
        cli_app,
        applied,
        publisher_client,
        subscriber_client,
        tmp_path
    ):
        file = tmp_path / "exported.yaml"
        result = run(cli_runner, cli_app, "export", file)
        assert "Exported 2 topic(s) and 2 subscription(s)" in " ".join(
            result.stdout.split()
        )

        other = f"{constants.PROJECT_PREFIX}-{uuid.uuid4().hex[:12]}"
        try:
            run(cli_runner, cli_app, "-p", other, "apply", file)
            original = yaml.safe_load(run(cli_runner, cli_app, "export").stdout)
            copy = yaml.safe_load(
                run(cli_runner, cli_app, "-p", other, "export").stdout
            )
        finally:
            utils.cleanup_project(publisher_client, subscriber_client, other)
        assert copy == {**original, "project": other}

    def test_empty_project(self, cli_runner, cli_app):
        exported = yaml.safe_load(run(cli_runner, cli_app, "export").stdout)
        assert exported == {"project": utils.current_project(), "topics": {}}

    def test_does_not_overwrite_without_force(self, cli_runner, cli_app, tmp_path):
        file = tmp_path / "pubsub.yaml"
        file.write_text("original")
        run(cli_runner, cli_app, "export", file, exit_code=1)
        assert file.read_text() == "original"

        run(cli_runner, cli_app, "export", file, "--force")
        assert yaml.safe_load(file.read_text())["topics"] == {}

    def test_skips_temporary_tail_subscriptions(
        self,
        cli_runner,
        cli_app,
        ready_topic,
        subscriber_client
    ):
        subscriber_client.create_subscription(
            name=utils.get_subscription_path(
                subscriber_client, subscription_name="pk-tail-leftover"
            ),
            topic=ready_topic,
        )
        exported = yaml.safe_load(run(cli_runner, cli_app, "export").stdout)
        assert exported["topics"] == {TOPIC: None}

    def test_warns_about_subscription_of_deleted_topic(
        self,
        cli_runner,
        cli_app,
        ready_subscription,
        publisher_client
    ):
        topic_path, _ = ready_subscription
        publisher_client.delete_topic(topic=topic_path)

        result = run(cli_runner, cli_app, "export")
        # o stdout continua sendo só o YAML
        assert yaml.safe_load(result.stdout)["topics"] == {}
        assert f"Skipping subscription '{WORKER}'" in " ".join(result.stderr.split())

    def test_json_output_can_be_applied(
        self,
        cli_runner,
        cli_app,
        applied,
        tmp_path
    ):
        exported = json.loads(run(cli_runner, cli_app, "export", "-o", "json").stdout)
        assert exported["topics"][DLQ_TOPIC] == {}
        assert exported["topics"][TOPIC]["subscriptions"][0] == WORKER

        file = tmp_path / "exported.json"
        file.write_text(json.dumps(exported))
        result = run(cli_runner, cli_app, "apply", file, "-o", "json")
        statuses = {r["status"] for r in json.loads(result.stdout)["resources"]}
        assert statuses == {"exists"}
