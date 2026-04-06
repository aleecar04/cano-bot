import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


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
    full_name: str | None = Field(default=None, max_length=255)


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
    xmpp_account: str | None = None


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


class MessagePublic(BaseModel):
    id: uuid.UUID
    from_user_id: uuid.UUID
    command_id: uuid.UUID | None = None
    xmpp_message_id: str | None = None
    body: str
    response: str | None = None
    created_at: datetime | None = None


class BaseUserPublic(BaseModel):
    id: uuid.UUID
    username: str
    jid: str
    created_at: datetime | None = None


class BotWebhookPayload(BaseModel):
    from_jid: str
    body: str
    response: str
    message_id: str | None = None


class PrivateUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None