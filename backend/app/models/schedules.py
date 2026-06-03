import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.base import DeviceActionBase


class GroupScheduleCreate(BaseModel):
    """Body for room/floor bulk-schedule endpoints (device_id is assigned server-side)."""
    name: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=50)
    payload: dict = {}
    run_at: datetime | None = None
    cron_expr: str | None = None
    timezone: str = "UTC"


class ScheduleCreate(DeviceActionBase):
    name: str = Field(min_length=1, max_length=100)
    run_at: datetime | None = None
    cron_expr: str | None = None
    timezone: str = "UTC"


class SchedulePublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    device_id: uuid.UUID
    name: str
    action: str
    payload: dict
    cron_expr: str | None = None
    next_run_at: datetime
    is_active: bool
    last_command_id: uuid.UUID | None = None
    created_at: datetime | None = None


class ScheduleMarkRun(BaseModel):
    command_id: str


class ScheduleToggle(BaseModel):
    is_active: bool
