import pytest

from pubsub_knife import constants as src_constants
from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.publisher,
]


def pull_all(cli_runner, cli_app) -> str:
    return utils.invoke_command(
        cli_runner=cli_runner,
        cli_app=cli_app,
        command="pull",
        command_args=[constants.TEST_SUBSCRIPTION, "-n", 10, "--ack"]
    )


class TestPublisher:

    def test_publish(
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
            command="pub",
            command_args=[constants.TEST_TOPIC, expected_message]
        )
        assert src_constants.MESSAGE_PUBLISHING.format(topic_path) in result
        assert "Message published with ID" in result

        result = pull_all(cli_runner, cli_app)
        assert src_constants.MESSAGE_NO_RESULT not in result
        assert expected_message in result

    def test_publish_should_error_when_send_invalid_json(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pub",
            command_args=[constants.TEST_TOPIC, "teste", "--json"],
            exit_code=1
        )
        assert src_constants.MESSAGE_PUBLISH_INVALID_JSON in result

    def test_publish_from_file(
        self,
        cli_runner,
        cli_app,
        ready_subscription,
        tmp_path
    ):
        _ = ready_subscription
        payload = tmp_path / "payload.json"
        payload.write_text('{"order_id": 42}')

        utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pub",
            command_args=[constants.TEST_TOPIC, f"@{payload}", "--json"]
        )
        assert '{"order_id": 42}' in pull_all(cli_runner, cli_app)

    def test_publish_from_stdin(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription
        result = cli_runner.invoke(
            cli_app, ["pub", constants.TEST_TOPIC, "-"], input="from_stdin"
        )
        assert result.exit_code == 0, result.output
        assert "from_stdin" in pull_all(cli_runner, cli_app)

    def test_publish_should_error_when_file_not_found(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pub",
            command_args=[constants.TEST_TOPIC, "@nao-existe.json"],
            exit_code=1
        )
        assert "File not found" in result

    def test_publish_with_gzip_is_decoded_on_pull(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription
        expected_message = "gzipped_message"

        utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pub",
            command_args=[constants.TEST_TOPIC, expected_message, "--gzip"]
        )
        result = pull_all(cli_runner, cli_app)
        assert expected_message in result
        assert "gzip" in result

    def test_publish_with_repeat_and_interval(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription
        expected_interval = 0.1

        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pub",
            command_args=[
                constants.TEST_TOPIC,
                "repeated",
                "--repeat",
                3,
                "--interval",
                expected_interval
            ]
        )
        assert result.count("Message published with ID") == 3
        assert result.count(
            src_constants.MESSAGE_PUBLISHED_INTERVAL.format(expected_interval)
        ) == 2
        assert pull_all(cli_runner, cli_app).count("repeated") == 3

    def test_publish_to_unexists_topic(
        self,
        cli_runner,
        cli_app
    ):
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pub",
            command_args=[constants.TEST_TOPIC, "lost"],
            exit_code=1
        )
        assert "Failed to publish message" in result

    def test_publish_with_attributes_and_ordering_key(
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
            command_args=[
                constants.TEST_TOPIC, "with_attrs",
                "-a", "type=created", "--attr", "source=test",
                "--ordering-key", "customer-1"
            ]
        )
        result = pull_all(cli_runner, cli_app)
        assert "'type': 'created'" in result
        assert "'source': 'test'" in result
        assert "'ordering_key': 'customer-1'" in result

    def test_publish_lines(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription
        result = cli_runner.invoke(
            cli_app,
            ["pub", constants.TEST_TOPIC, "--lines"],
            input="first\n\nsecond\nthird\n"
        )
        assert result.exit_code == 0, result.output
        assert "Published 3 message(s)" in result.output

        result = pull_all(cli_runner, cli_app)
        for expected in ("first", "second", "third"):
            assert expected in result

    def test_publish_envelope_replays_tail_capture(
        self,
        cli_runner,
        cli_app,
        ready_subscription,
        tmp_path
    ):
        _ = ready_subscription
        utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pub",
            command_args=[
                constants.TEST_TOPIC, "captured", "-a", "type=x", "-k", "k1", "--gzip"
            ]
        )
        capture = cli_runner.invoke(
            cli_app,
            ["tail", constants.TEST_SUBSCRIPTION, "--jsonl", "-n", 1,
             "--timeout", 10, "--ack"],
        )
        assert capture.exit_code == 0, capture.output
        capture_file = tmp_path / "capture.jsonl"
        capture_file.write_text(
            "\n".join(
                line for line in capture.stdout.splitlines() if line.startswith("{")
            )
        )

        utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pub",
            command_args=[constants.TEST_TOPIC, f"@{capture_file}", "--envelope"]
        )
        result = pull_all(cli_runner, cli_app)
        assert "'data': 'captured'" in result
        assert "'type': 'x'" in result
        assert "'encoding': 'gzip'" in result
        assert "'ordering_key': 'k1'" in result

    def test_publish_invalid_attribute(
        self,
        cli_runner,
        cli_app,
        ready_subscription
    ):
        _ = ready_subscription
        result = utils.invoke_command(
            cli_runner=cli_runner,
            cli_app=cli_app,
            command="pub",
            command_args=[constants.TEST_TOPIC, "x", "-a", "invalid"],
            exit_code=1
        )
        assert "Invalid attribute" in result
