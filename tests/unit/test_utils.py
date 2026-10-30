import gzip
import os

import pytest
import typer
from google.pubsub_v1.types import PubsubMessage

from pubsub_knife.config import EmulatorUnavailableError, Settings
from pubsub_knife.consumer import decode_message
from pubsub_knife.main import app
from pubsub_knife.publisher import build_payload

pytestmark = [
    pytest.mark.unit,
    pytest.mark.utils,
]


class TestSettings:

    def test_configure_emulator_exports_env(self, monkeypatch):
        monkeypatch.delenv("PUBSUB_EMULATOR_HOST", raising=False)
        Settings(pubsub_emulator_host="emulator:9999").configure_emulator()
        assert os.environ["PUBSUB_EMULATOR_HOST"] == "emulator:9999"

    def test_check_emulator_unreachable(self):
        settings = Settings(
            pubsub_emulator_host="127.0.0.1:1", pubsub_connect_timeout=0.5
        )
        with pytest.raises(EmulatorUnavailableError):
            settings.check_emulator()

    def test_check_emulator_invalid_host(self):
        with pytest.raises(EmulatorUnavailableError):
            Settings(pubsub_emulator_host="localhost").check_emulator()

    def test_cli_fails_fast_when_emulator_is_down(self, cli_runner):
        result = cli_runner.invoke(
            app, ["--emulator-host", "127.0.0.1:1", "topic", "list"]
        )
        assert result.exit_code == 1
        assert "not reachable" in result.output

    def test_help_does_not_require_emulator(self, cli_runner):
        result = cli_runner.invoke(
            app, ["--emulator-host", "127.0.0.1:1", "topic", "--help"]
        )
        assert result.exit_code == 0


class TestPayload:

    def test_build_payload_plain(self):
        assert build_payload("hello", False, False) == (b"hello", {})

    def test_build_payload_gzip(self):
        content, attributes = build_payload("hello", False, True)
        assert gzip.decompress(content) == b"hello"
        assert attributes == {"encoding": "gzip"}

    def test_build_payload_invalid_json(self):
        with pytest.raises(typer.Exit):
            build_payload("{invalid", True, False)


class TestDecodeMessage:

    def test_decode_gzip(self):
        message = PubsubMessage(
            data=gzip.compress(b"hello"), attributes={"encoding": "gzip"}
        )
        assert decode_message(message)["data"] == "hello"

    def test_decode_binary_does_not_crash(self):
        message = PubsubMessage(data=b"\xff\xfe")
        assert decode_message(message)["data"] == repr(b"\xff\xfe")

    def test_decode_invalid_gzip_keeps_raw_content(self):
        message = PubsubMessage(data=b"plain", attributes={"encoding": "gzip"})
        assert decode_message(message)["data"] == "plain"

