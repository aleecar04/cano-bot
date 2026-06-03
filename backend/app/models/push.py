from pydantic import BaseModel


class PushSubscriptionBody(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
