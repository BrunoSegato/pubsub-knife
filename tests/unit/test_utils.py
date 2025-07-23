import pytest

from src.utils import callback

pytestmark = [
    pytest.mark.unit,
    pytest.mark.utils,
]

class TestUtils:

    def test_callback_success(self, mocker, capsys):
        mock_future = mocker.Mock()
        mock_future.result.return_value = "msg-123"

        callback(mock_future)

        captured = capsys.readouterr()
        assert "🎯 Callback: Mensagem publicada com ID msg-123" in captured.out

    def test_callback_failure(self, mocker, capsys):
        mock_future = mocker.Mock()
        mock_future.result.side_effect = Exception("Simulated failure")

        callback(mock_future)

        captured = capsys.readouterr()
        expected_message = "❌ Callback: Falha ao publicar mensagem: Simulated failure"
        assert expected_message in captured.out
