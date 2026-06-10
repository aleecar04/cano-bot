import uuid
from datetime import datetime
from pydantic import BaseModel


class CommandRequest(BaseModel):
    """Petición unificada de comando: device (con device_id) o system (sin él, p.ej. scan)."""
    action: str
    device_id: uuid.UUID | None = None
    payload: dict = {}


class CommandPublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    device_id: uuid.UUID | None = None
    target_type: str = "device"
    action: str
    payload: dict = {}
    status: str
    source_type: str = "direct"
    source_id: uuid.UUID | None = None
    error: str | None = None
    result_data: dict | None = None  # estructura de queries (scan, list_devices); NULL en acciones
    executed_at: datetime | None = None
    created_at: datetime | None = None
