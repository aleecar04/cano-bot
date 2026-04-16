import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    email: EmailStr = Field(max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(BaseModel):
    email: EmailStr = Field(max_length=255)
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        import re
        if not re.fullmatch(r"[a-z0-9_]{3,50}", v):
            raise ValueError("El usuario solo puede tener letras minúsculas, números y guiones bajos")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        import re
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contraseña debe incluir al menos una letra mayúscula")
        if not re.search(r"\d", v):
            raise ValueError("La contraseña debe incluir al menos un número")
        return v


class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UserProfilePublic(UserPublic):
    email: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    xmpp_jid: str | None = None


class UsersPublic(BaseModel):
    data: list[UserPublic]
    count: int


class Message(BaseModel):
    message: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    model_config = {"extra": "ignore"}
    sub: str | None = None


class NewPassword(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class MessageCreate(BaseModel):
    body: str
    conversation_id: uuid.UUID | None = None


class MessagePublic(BaseModel):
    id: uuid.UUID
    from_user_id: uuid.UUID
    command_id: uuid.UUID | None = None
    xmpp_message_id: str | None = None
    conversation_id: uuid.UUID | None = None  # <-- nuevo
    body: str
    response: str | None = None
    created_at: datetime | None = None

class BaseUserPublic(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None = None
    full_name: str | None = None
    created_at: datetime | None = None


class XmppAccountPublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    jid: str
    status: str = "offline"
    last_connection: datetime | None = None
    created_at: datetime | None = None


class XmppAccountCreate(BaseModel):
    jid: str
    password: str


class BotWebhookPayload(BaseModel):
    from_jid: str
    body: str
    response: str
    message_id: str | None = None


class PrivateUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    
class RoomPublic(BaseModel):
    id: uuid.UUID
    floor_id: uuid.UUID
    name: str

class FloorPublic(BaseModel):
    id: uuid.UUID
    house_id: uuid.UUID
    name: str
    level: int = 0
    rooms: list[RoomPublic] = []

class HousePublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str | None = None
    floors: list[FloorPublic] = []

class FloorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    level: int = 0

class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

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
    name: str
    type: str
    driver: str | None = None
    ip: str
    location: str | None = None
    config: dict = {}
    estado: dict = {}
    is_online: bool
    last_seen_at: datetime | None = None
    registered_at: datetime | None = None

class DeviceStatusUpdate(BaseModel):
    is_online: bool
    estado: dict = {}

class CommandCreate(BaseModel):
    accion: str
    payload: dict = {}
    
class ConversationCreate(BaseModel):
    title: str | None = None

class ConversationPublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ConversationsPublic(BaseModel):
    data: list[ConversationPublic]
    count: int


# ── Schedules ─────────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    device_id: uuid.UUID
    name: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=50)
    payload: dict = {}
    run_at: datetime | None = None       # one-time
    cron_expr: str | None = None         # recurring, e.g. "30 22 * * *"
    is_recurring: bool = False


class SchedulePublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    device_id: uuid.UUID
    name: str
    action: str
    payload: dict
    run_at: datetime | None = None
    cron_expr: str | None = None
    next_run_at: datetime
    is_recurring: bool
    is_active: bool
    last_run_at: datetime | None = None
    last_status: str | None = None
    last_error: str | None = None
    created_at: datetime | None = None


class ScheduleMarkRun(BaseModel):
    status: str   # 'ok' or 'error'
    error: str | None = None


class ScheduleToggle(BaseModel):
    is_active: bool


# ── Favorite actions ──────────────────────────────────────────────────────────

class FavoriteActionCreate(BaseModel):
    device_id: uuid.UUID
    action: str = Field(min_length=1, max_length=50)
    payload: dict = {}
    label: str | None = Field(default=None, max_length=80)


class FavoriteActionPublic(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    device_id: uuid.UUID
    action: str
    payload: dict
    label: str | None = None
    position: int
    created_at: datetime | None = None
    devices: dict | None = None   # joined: {name, type}