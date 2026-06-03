from unittest.mock import patch, MagicMock


class TestResolveInHouse:

    def test_returns_user_id_when_member(self):
        from api import users
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"user_id": "u-1"}
        with patch("api._client.get", return_value=mock_resp) as mock_get:
            assert users.resolve_in_house("alice@example.com") == "u-1"
        path = mock_get.call_args[0][0]
        assert path == "/api/v1/users/resolve"
        assert mock_get.call_args.kwargs["params"] == {"jid": "alice@example.com"}

    def test_returns_none_when_not_member(self):
        from api import users
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"user_id": None}
        with patch("api._client.get", return_value=mock_resp):
            assert users.resolve_in_house("intruso@example.com") is None
