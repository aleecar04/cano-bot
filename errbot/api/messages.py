from api import _client


def log_webhook(from_jid: str, body: str, response: str, message_id: str | None = None) -> None:
    _client.post(
        "/api/v1/messages/webhook",
        json={
            "from_jid":   from_jid,
            "body":       body,
            "response":   response,
            "message_id": message_id,
        },
        timeout=3,
    )


def forward_from_gajim(from_jid: str, body: str) -> None:
    """Reenvía un mensaje natural recibido desde un cliente XMPP directo (Gajim)
    al backend, que clasifica y dispatcha. """
    _client.post(
        "/api/v1/messages/from-gajim",
        json={"from_jid": from_jid, "body": body},
        timeout=10,
    )
