from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.parametrize("backend_user_id, expected", [
    ("u-1", "u-1"),
    (None, None)
])
def test_resolve_in_house_returns_user_id_or_none(backend_user_id, expected):
    from api import users
    mock_resp = MagicMock(); mock_resp.json.return_value = {"user_id": backend_user_id}
    with patch("api._client.get", return_value=mock_resp) as mock_get:
        assert users.resolve_in_house("alice@example.com") == expected
    assert mock_get.call_args[0][0] == "/api/v1/users/resolve"
    assert mock_get.call_args.kwargs["params"] == {"jid": "alice@example.com"}
