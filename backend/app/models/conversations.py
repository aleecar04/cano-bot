import uuid
from datetime import datetime
from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationPublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
