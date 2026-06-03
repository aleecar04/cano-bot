from unittest.mock import patch


class TestLogWebhook:

    def test_sends_message_payload(self):
        from api import messages
        with patch("api._client.post") as mock_post:
            messages.log_webhook("alice@x", "hola", "buenas", message_id="m-1")
        path = mock_post.call_args[0][0]
        assert path == "/api/v1/messages/webhook"
        body = mock_post.call_args.kwargs["json"]
        assert body == {
            "from_jid":   "alice@x",
            "body":       "hola",
            "response":   "buenas",
            "message_id": "m-1",
        }

    def test_message_id_defaults_to_none(self):
        from api import messages
        with patch("api._client.post") as mock_post:
            messages.log_webhook("alice@x", "hola", "buenas")
        assert mock_post.call_args.kwargs["json"]["message_id"] is None
