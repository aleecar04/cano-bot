import uuid
from datetime import datetime
from pydantic import BaseModel


class DeviceVincular(BaseModel):
    ip: str
    mac: str
    hostname: str
    tipo: str
    name: str
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
    estado: dict = {}
    is_online: bool
    room_id: uuid.UUID | None = None
    last_seen_at: datetime | None = None
    registered_at: datetime | None = None
    updated_at: datetime | None = None


class DeviceUpdate(BaseModel):
    name: str | None = None
    room_id: uuid.UUID | None = None
    type: str | None = None


class DeviceStatusUpdate(BaseModel):
    is_online: bool
    estado: dict = {}


class HAConnectSchema(BaseModel):
    """Body for /devices/ha/connect — Home Assistant credentials."""
    ha_url: str
    token: str
