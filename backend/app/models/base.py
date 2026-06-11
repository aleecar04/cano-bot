import uuid
from pydantic import BaseModel, Field


class DeviceActionBase(BaseModel):
    device_id: uuid.UUID
    action:    str = Field(min_length=1, max_length=50)
    payload:   dict = {}
