from unittest.mock import MagicMock, patch


def test_patch_result_serializes_error_and_result_data():
    from api import commands
    with patch("api._client.patch") as mock_patch:
        commands.patch_result("cmd-1", error="timeout", result_data={"tipo": "scan"})
    assert mock_patch.call_args[0][0] == "/api/v1/commands/cmd-1"
    assert mock_patch.call_args.kwargs["json"] == {
        "error": "timeout", "result_data": {"tipo": "scan"},
    }


def test_patch_result_defaults_result_data_to_none():
    from api import commands
    with patch("api._client.patch") as mock_patch:
        commands.patch_result("cmd-1", error=None)
    assert mock_patch.call_args.kwargs["json"]["result_data"] is None


def test_register_from_bot_omits_target_type():
    from api import commands
    mock_resp = MagicMock(); mock_resp.json.return_value = {"ok": True, "command_id": "cmd-1"}
    with patch("api._client.post", return_value=mock_resp) as mock_post:
        result = commands.register_from_bot(
            user_id="u1", device_id="d1", action="encender",
            payload={"v": 1}, error=None, message_id="msg-1", result_data=None,
        )
    assert result == {"ok": True, "command_id": "cmd-1"}
    body = mock_post.call_args.kwargs["json"]
    assert body["user_id"] == "u1" and body["action"] == "encender"
    assert "target_type" not in body


def test_register_pending_from_bot_sets_pending_flag():
    from api import commands
    mock_resp = MagicMock(); mock_resp.json.return_value = {"ok": True, "command_id": "cmd-2"}
    with patch("api._client.post", return_value=mock_resp) as mock_post:
        commands.register_pending_from_bot(
            user_id="u1", device_id="d1", action="encender",
            payload={"v": 1}, message_id="msg-1",
        )
    body = mock_post.call_args.kwargs["json"]
    assert body["pending"] is True and "target_type" not in body
