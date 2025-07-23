import pytest

from src import constants
from src.utils import callback

pytestmark = [
    pytest.mark.unit,
    pytest.mark.utils,
]

class TestUtils:

    def test_callback_success(self, mocker, capsys):
        expected_message = "msg-123"
        mock_future = mocker.Mock()
        mock_future.result.return_value = expected_message

        callback(mock_future)

        captured = capsys.readouterr()
        assert constants.MESSAGE_PUBLISHED_WITH_CALLBACK.format(
            expected_message
        ) in captured.out

    def test_callback_failure(self, mocker, capsys):
        expected_message = "Simulated failure"
        mock_future = mocker.Mock()
        mock_future.result.side_effect = Exception(expected_message)

        callback(mock_future)

        captured = capsys.readouterr()
        assert constants.MESSAGE_PUBLISHED_ERROR_WITH_CALLBACK.format(
            expected_message
        ) in captured.out
