from unittest.mock import patch


def test_log_webhook_sends_message_payload_to_webhook_path():
    from api import messages
    with patch("api._client.post") as mock_post:
        messages.log_webhook("alice@x", "hola", "buenas", message_id="m-1")
    assert mock_post.call_args[0][0] == "/api/v1/messages/webhook"
    assert mock_post.call_args.kwargs["json"] == {
        "from_jid":   "alice@x",
        "body":       "hola",
        "response":   "buenas",
        "message_id": "m-1",
    }


def test_log_webhook_defaults_message_id_to_none():
    from api import messages
    with patch("api._client.post") as mock_post:
        messages.log_webhook("alice@x", "hola", "buenas")
    assert mock_post.call_args.kwargs["json"]["message_id"] is None
