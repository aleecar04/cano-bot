import uuid
from pydantic import BaseModel, Field


class RoomPublic(BaseModel):
    id: uuid.UUID
    floor_id: uuid.UUID
    name: str


class FloorPublic(BaseModel):
    id: uuid.UUID
    house_id: uuid.UUID
    name: str
    rooms: list[RoomPublic] = []

class HousePublic(BaseModel):
    id: uuid.UUID
    name: str | None = None
    floors: list[FloorPublic] = []

class FloorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

class GroupActionRequest(BaseModel):
    action: str

class InviteCodeResponse(BaseModel):
    code: str
    expires_in_hours: int = 24

class JoinRequest(BaseModel):
    code: str

class HouseSetupRequest(BaseModel):
    name: str | None = Field(default=None, max_length=50)
