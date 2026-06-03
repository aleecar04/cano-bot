import time
import pytest
from unittest.mock import patch, MagicMock
import requests


@pytest.fixture(autouse=True)
def reset_cache():
    """Resetea el cache de reachable entre tests."""
    import api._client as client
    client._last_backend_check = 0.0
    client._backend_available = True
    yield
    client._last_backend_check = 0.0
    client._backend_available = True


# ── is_backend_reachable ─────────────────────────────────────────────────────

class TestIsBackendReachable:

    def test_returns_true_when_health_returns_200(self):
        from api import is_backend_reachable
        mock_resp = MagicMock(status_code=200)
        with patch("requests.get", return_value=mock_resp):
            assert is_backend_reachable() is True

    def test_returns_false_when_health_returns_500(self):
        from api import is_backend_reachable
        mock_resp = MagicMock(status_code=500)
        with patch("requests.get", return_value=mock_resp):
            assert is_backend_reachable() is False

    def test_returns_false_when_connection_refused(self):
        from api import is_backend_reachable
        with patch("requests.get", side_effect=ConnectionError("refused")):
            assert is_backend_reachable() is False

    def test_result_is_cached_within_interval(self):
        from api import is_backend_reachable
        mock_resp = MagicMock(status_code=200)
        with patch("requests.get", return_value=mock_resp) as mock_get:
            is_backend_reachable()
            is_backend_reachable()
        assert mock_get.call_count == 1

    def test_cache_expires_after_interval(self):
        import api._client as client
        from api import is_backend_reachable
        mock_resp = MagicMock(status_code=200)
        client._last_backend_check = time.monotonic() - 999
        with patch("requests.get", return_value=mock_resp) as mock_get:
            is_backend_reachable()
            is_backend_reachable()  # cache caducado pero ahora vuelve a estar dentro de la ventana
        assert mock_get.call_count == 1


# ── _request / get / post / patch ────────────────────────────────────────────

class TestRequestWrappers:

    def test_get_adds_backend_url_prefix(self):
        from api import _client
        mock_resp = MagicMock()
        with patch("requests.get", return_value=mock_resp) as mock_req:
            _client.get("/api/v1/foo")
        called_url = mock_req.call_args[0][0]
        assert called_url.endswith("/api/v1/foo")

    def test_post_includes_auth_header(self):
        from api import _client
        mock_resp = MagicMock()
        with patch("requests.post", return_value=mock_resp) as mock_req:
            _client.post("/x", json={"k": "v"})
        called_headers = mock_req.call_args.kwargs["headers"]
        assert "Authorization" in called_headers

    def test_patch_raises_on_http_error(self):
        from api import _client
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("4xx")
        with patch("requests.patch", return_value=mock_resp), \
             pytest.raises(requests.HTTPError):
            _client.patch("/y", json={})

    def test_extra_headers_merge_without_dropping_auth(self):
        from api import _client
        mock_resp = MagicMock()
        with patch("requests.get", return_value=mock_resp) as mock_req:
            _client.get("/x", headers={"X-Custom": "v"})
        sent = mock_req.call_args.kwargs["headers"]
        assert sent["X-Custom"] == "v"
        assert "Authorization" in sent
