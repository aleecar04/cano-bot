from pydantic import BaseModel


class BotWebhookPayload(BaseModel):
    from_jid: str
    body: str
    response: str
    message_id: str | None = None


class GajimMessagePayload(BaseModel):
    from_jid: str
    body: str
