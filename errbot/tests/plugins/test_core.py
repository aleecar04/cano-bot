from unittest.mock import MagicMock, patch

import pytest
import requests as requests_lib


@pytest.fixture(autouse=True)
def reset_backend_cache():
    import api._client as client
    client._last_backend_check = 0.0
    client._backend_available = True
    yield
    client._last_backend_check = 0.0
    client._backend_available = True


class TestLogMessage:

    def _make_plugin(self):
        from plugins._core import BasePlugin
        return BasePlugin()

    def test_skipped_when_backend_unreachable(self):
        with patch("plugins._core.is_backend_reachable", return_value=False), \
             patch("api.messages.log_webhook") as mock_log:
            self._make_plugin().log_message("user@host", "hello", "world")
        mock_log.assert_not_called()

    def test_posts_to_webhook_when_reachable(self):
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("api.messages.log_webhook") as mock_log:
            self._make_plugin().log_message("user@host", "hello", "world", message_id="msg-1")
        mock_log.assert_called_once_with("user@host", "hello", "world", "msg-1")

    def test_swallows_network_or_runtime_errors_from_webhook(self):
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("api.messages.log_webhook", side_effect=requests_lib.Timeout()):
            self._make_plugin().log_message("u", "b", "r")
