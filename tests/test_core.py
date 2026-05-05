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
    import plugins._core as core
    core._last_backend_check = 0.0
    core._backend_available = True
    yield
    core._last_backend_check = 0.0
    core._backend_available = True


def test_reachable_when_health_returns_200():
    from plugins._core import is_backend_reachable
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp):
        assert is_backend_reachable() is True


def test_unreachable_when_health_returns_500():
    from plugins._core import is_backend_reachable
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    with patch("requests.get", return_value=mock_resp):
        assert is_backend_reachable() is False


def test_unreachable_when_request_raises():
    from plugins._core import is_backend_reachable
    with patch("requests.get", side_effect=ConnectionError("refused")):
        assert is_backend_reachable() is False


def test_result_is_cached_within_interval():
    from plugins._core import is_backend_reachable
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp) as mock_get:
        is_backend_reachable()
        is_backend_reachable() 
    assert mock_get.call_count == 1


def test_cache_expires_after_interval():
    import plugins._core as core
    from plugins._core import is_backend_reachable
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    core._last_backend_check = time.monotonic() - 999
    with patch("requests.get", return_value=mock_resp) as mock_get:
        is_backend_reachable()
        is_backend_reachable()
    assert mock_get.call_count == 1


class TestLogMessage:
    def _make_plugin(self):
        from plugins._core import BasePlugin
        p = BasePlugin()
        return p

    def test_log_message_skipped_when_backend_unreachable(self):
        p = self._make_plugin()
        with patch("plugins._core.is_backend_reachable", return_value=False), \
             patch("requests.post") as mock_post:
            p.log_message("user@host", "hello", "world")
        mock_post.assert_not_called()

    def test_log_message_posts_to_webhook(self):
        p = self._make_plugin()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("requests.post", return_value=mock_resp) as mock_post:
            p.log_message("user@host", "hello", "world", message_id="msg-1")
        mock_post.assert_called_once()
        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["from_jid"] == "user@host"
        assert call_json["body"] == "hello"

    def test_log_message_handles_timeout(self):
        p = self._make_plugin()
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("requests.post", side_effect=requests_lib.Timeout()):
            p.log_message("u", "b", "r")

    def test_log_message_handles_http_error(self):
        p = self._make_plugin()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        err = requests_lib.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = err
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("requests.post", return_value=mock_resp):
            p.log_message("u", "b", "r") 

    def test_log_message_handles_generic_exception(self):
        p = self._make_plugin()
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("requests.post", side_effect=RuntimeError("unexpected")):
            p.log_message("u", "b", "r")


class TestUpdateDeviceStatus:
    def _make_plugin(self):
        from plugins._core import BasePlugin
        return BasePlugin()

    def test_skipped_when_backend_unreachable(self):
        p = self._make_plugin()
        with patch("plugins._core.is_backend_reachable", return_value=False), \
             patch("requests.patch") as mock_patch:
            p.update_device_status("dev-1", True)
        mock_patch.assert_not_called()

    def test_patches_device_status(self):
        p = self._make_plugin()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("requests.patch", return_value=mock_resp) as mock_patch:
            p.update_device_status("dev-1", is_online=True, estado={"power": "on"})
        mock_patch.assert_called_once()
        assert "dev-1" in mock_patch.call_args.args[0]

    def test_handles_timeout(self):
        p = self._make_plugin()
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("requests.patch", side_effect=requests_lib.Timeout()):
            p.update_device_status("dev-1", True) 

    def test_handles_generic_exception(self):
        p = self._make_plugin()
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("requests.patch", side_effect=RuntimeError("fail")):
            p.update_device_status("dev-1", True) 
