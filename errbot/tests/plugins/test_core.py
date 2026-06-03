"""
All HTTP calls are mocked.
"""
import time
import pytest
from unittest.mock import patch, MagicMock
import requests as requests_lib

@pytest.fixture(autouse=True)
def reset_backend_cache():
    """Force is_backend_reachable to re-check on each test."""
    import api._client as client
    client._last_backend_check = 0.0
    client._backend_available = True
    yield
    client._last_backend_check = 0.0
    client._backend_available = True


def test_reachable_when_health_returns_200():
    from api import is_backend_reachable
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp):
        assert is_backend_reachable() is True


def test_unreachable_when_health_returns_500():
    from api import is_backend_reachable
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    with patch("requests.get", return_value=mock_resp):
        assert is_backend_reachable() is False


def test_unreachable_when_request_raises():
    from api import is_backend_reachable
    with patch("requests.get", side_effect=ConnectionError("refused")):
        assert is_backend_reachable() is False


def test_result_is_cached_within_interval():
    from api import is_backend_reachable
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp) as mock_get:
        is_backend_reachable()
        is_backend_reachable()
    assert mock_get.call_count == 1


def test_cache_expires_after_interval():
    import api._client as client
    from api import is_backend_reachable
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    client._last_backend_check = time.monotonic() - 999
    with patch("requests.get", return_value=mock_resp) as mock_get:
        is_backend_reachable()
        is_backend_reachable()
    assert mock_get.call_count == 1


class TestLogMessage:
    def _make_plugin(self):
        from plugins._core import BasePlugin
        return BasePlugin()

    def test_log_message_skipped_when_backend_unreachable(self):
        p = self._make_plugin()
        with patch("plugins._core.is_backend_reachable", return_value=False), \
             patch("api.messages.log_webhook") as mock_log:
            p.log_message("user@host", "hello", "world")
        mock_log.assert_not_called()

    def test_log_message_posts_to_webhook(self):
        p = self._make_plugin()
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("api.messages.log_webhook") as mock_log:
            p.log_message("user@host", "hello", "world", message_id="msg-1")
        mock_log.assert_called_once_with("user@host", "hello", "world", "msg-1")

    def test_log_message_handles_timeout(self):
        p = self._make_plugin()
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("api.messages.log_webhook", side_effect=requests_lib.Timeout()):
            p.log_message("u", "b", "r")

    def test_log_message_handles_http_error(self):
        p = self._make_plugin()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        err = requests_lib.HTTPError(response=mock_resp)
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("api.messages.log_webhook", side_effect=err):
            p.log_message("u", "b", "r")

    def test_log_message_handles_generic_exception(self):
        p = self._make_plugin()
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("api.messages.log_webhook", side_effect=RuntimeError("unexpected")):
            p.log_message("u", "b", "r")
