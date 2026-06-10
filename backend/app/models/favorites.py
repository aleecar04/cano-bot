import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.base import DeviceActionBase


class FavoriteActionCreate(DeviceActionBase):
    label: str | None = Field(default=None, max_length=50)


class FavoriteActionUpdate(BaseModel):
    action: str = Field(min_length=1, max_length=50)
    payload: dict = {}
    label: str | None = Field(default=None, max_length=50)


class FavoriteActionPublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    device_id: uuid.UUID
    action: str
    payload: dict
    label: str | None = None
    created_at: datetime | None = None
    devices: dict | None = None
