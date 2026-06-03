from unittest.mock import patch, MagicMock


class TestPatchResult:

    def test_sends_error_and_result_data(self):
        from api import commands
        with patch("api._client.patch") as mock_patch:
            commands.patch_result("cmd-1", error="timeout", result_data={"tipo": "scan"})
        path = mock_patch.call_args[0][0]
        assert path == "/api/v1/commands/cmd-1"
        assert mock_patch.call_args.kwargs["json"] == {
            "error": "timeout", "result_data": {"tipo": "scan"}
        }

    def test_result_data_defaults_to_none(self):
        from api import commands
        with patch("api._client.patch") as mock_patch:
            commands.patch_result("cmd-1", error=None)
        assert mock_patch.call_args.kwargs["json"]["result_data"] is None


class TestRegisterFromBot:
    """register_from_bot no envía target_type: el backend lo deduce a partir
    del action contra su catálogo (info/system) y de la presencia de device_id."""

    def test_serializes_all_fields(self):
        from api import commands
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "command_id": "cmd-1"}
        with patch("api._client.post", return_value=mock_resp) as mock_post:
            result = commands.register_from_bot(
                user_id="u1", device_id="d1", action="encender",
                payload={"v": 1}, error=None, message_id="msg-1",
                result_data=None,
            )
        assert result == {"ok": True, "command_id": "cmd-1"}
        body = mock_post.call_args.kwargs["json"]
        assert body["user_id"] == "u1"
        assert body["device_id"] == "d1"
        assert body["action"] == "encender"
        assert "target_type" not in body
        assert body["result_data"] is None

    def test_omits_target_type_for_info_action(self):
        from api import commands
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        with patch("api._client.post", return_value=mock_resp) as mock_post:
            commands.register_from_bot(
                user_id="u1", device_id=None, action="ayuda",
                payload={}, error=None, message_id=None,
            )
        body = mock_post.call_args.kwargs["json"]
        assert "target_type" not in body
        assert body["device_id"] is None
        assert body["action"] == "ayuda"


class TestRegisterPendingFromBot:
    """register_pending_from_bot marca pending=True y omite target_type."""

    def test_sets_pending_flag(self):
        from api import commands
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "command_id": "cmd-2"}
        with patch("api._client.post", return_value=mock_resp) as mock_post:
            commands.register_pending_from_bot(
                user_id="u1", device_id="d1", action="encender",
                payload={"v": 1}, message_id="msg-1",
            )
        body = mock_post.call_args.kwargs["json"]
        assert body["pending"] is True
        assert "target_type" not in body
        assert body["action"] == "encender"
