import pytest

from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
    pytest.mark.publisher,
]

class TestPublisher:

    def test_publisher_publish_sync(self, cli_runner, cli_app, publisher_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)
        utils.create_subscription(cli_runner=cli_runner, cli_app=cli_app)

        topic_path = utils.get_topic_path(publisher_client)
        result = cli_runner.invoke(
            cli_app,
            [
                "publisher",
                "sync",
                "--topic",
                constants.TEST_TOPIC,
                "--message",
                "mensagem_teste"
            ]
        )
        assert result.exit_code == 0
        assert f"Publicando (sync) em {topic_path}" in result.stdout
        assert "Mensagem publicada com ID:" in result.stdout

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
        assert "Nenhuma mensagem encontrada." not in result.stdout
        assert "mensagem_teste" in result.stdout

    def test_publisher_with_callback(self, cli_runner, cli_app, publisher_client):
        utils.create_topic(cli_runner=cli_runner, cli_app=cli_app)
        utils.create_subscription(cli_runner=cli_runner, cli_app=cli_app)

        topic_path = utils.get_topic_path(publisher_client)
        result = cli_runner.invoke(
            cli_app,
            [
                "publisher",
                "with-callback",
                "--topic",
                constants.TEST_TOPIC,
                "--message",
                "callback_mensagem_teste"
            ]
        )
        assert result.exit_code == 0
        assert f"Publicando (callback) em {topic_path}" in result.stdout
        assert "Mensagem enviada para fila (callback será chamado)." in result.stdout
        assert "Callback: Mensagem publicada com ID" in result.stdout

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
        assert "Nenhuma mensagem encontrada." not in result.stdout
        assert "callback_mensagem_teste" in result.stdout
