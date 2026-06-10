from unittest.mock import MagicMock, patch

import pytest
import requests


@pytest.fixture(autouse=True)
def reset_cache():
    import api._client as client
    client._last_backend_check = 0.0
    client._backend_available = True
    yield
    client._last_backend_check = 0.0
    client._backend_available = True


@pytest.mark.parametrize("status_code, expected", [
    (200, True),
    (500, False),
])
def test_is_backend_reachable_based_on_status_code(status_code, expected):
    from api import is_backend_reachable
    with patch("requests.get", return_value=MagicMock(status_code=status_code)):
        assert is_backend_reachable() is expected


def test_unreachable_on_connection_refused():
    from api import is_backend_reachable
    with patch("requests.get", side_effect=ConnectionError("refused")):
        assert is_backend_reachable() is False


def test_get_prefixes_url_and_merges_headers():
    from api import _client
    with patch("requests.get", return_value=MagicMock()) as mock_req:
        _client.get("/api/v1/foo", headers={"X-Custom": "v"})
    assert mock_req.call_args[0][0].endswith("/api/v1/foo")
    sent = mock_req.call_args.kwargs["headers"]
    assert sent["X-Custom"] == "v" and "Authorization" in sent


def test_post_includes_auth_header():
    from api import _client
    with patch("requests.post", return_value=MagicMock()) as mock_req:
        _client.post("/x", json={"k": "v"})
    assert "Authorization" in mock_req.call_args.kwargs["headers"]


def test_patch_raises_on_http_error():
    from api import _client
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("4xx")
    with patch("requests.patch", return_value=mock_resp), \
         pytest.raises(requests.HTTPError):
        _client.patch("/y", json={})
