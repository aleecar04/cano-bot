from pydantic import BaseModel


class BotWebhookPayload(BaseModel):
    from_jid: str
    body: str
    response: str
    message_id: str | None = None


class GajimMessagePayload(BaseModel):
    """Mensaje natural que el bot reenvía al backend desde un cliente XMPP directo
    (Gajim u otro). El backend lo persiste, clasifica y orquesta el dispatch."""
    from_jid: str
    body: str
