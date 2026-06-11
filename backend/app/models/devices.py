import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class DeviceVincular(BaseModel):
    ip: str
    mac: str
    hostname: str
    tipo: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=50)
    room_id: uuid.UUID | None = None
    driver: str | None = None
    config: dict | None = None


class DevicePublic(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    house_id: uuid.UUID | None = None
    name: str
    type: str
    driver: str | None = None
    ip: str | None = None
    mac: str | None = None
    location: str | None = None
    config: dict = {}
    state: dict = {}
    is_online: bool
    room_id: uuid.UUID | None = None
    last_seen_at: datetime | None = None
    registered_at: datetime | None = None
    updated_at: datetime | None = None


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    room_id: uuid.UUID | None = None
    type: str | None = Field(default=None, min_length=1, max_length=50)


class DeviceStatusUpdate(BaseModel):
    is_online: bool
    state: dict = {}


class HAConnectSchema(BaseModel):
    ha_url: str
    token: str
