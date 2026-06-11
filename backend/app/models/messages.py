import uuid
from datetime import datetime
from pydantic import BaseModel

from app.models.commands import CommandPublic


class MessageCreate(BaseModel):
    body: str
    conversation_id: uuid.UUID


class MessagePublic(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    command_id: uuid.UUID | None = None
    body: str
    response: str | None = None
    created_at: datetime | None = None
    command: CommandPublic | None = None
