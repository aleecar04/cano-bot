import re
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
        if not re.fullmatch(r"[a-z0-9_]{3,50}", v):
            raise ValueError("El usuario solo puede tener letras minúsculas, números y guiones bajos")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contraseña debe incluir al menos una letra mayúscula")
        if not re.search(r"\d", v):
            raise ValueError("La contraseña debe incluir al menos un número")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = " ".join(v.strip().split())
        if not cleaned:
            return None
        if not re.fullmatch(r"[A-Za-zÀ-ÿñÑ\s\-']+", cleaned):
            raise ValueError("Solo se permiten letras, espacios, guiones y apóstrofes")
        return cleaned.title()


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


class BaseUserPublic(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None = None
    full_name: str | None = None
    created_at: datetime | None = None


class RegisterResponse(BaseUserPublic):
    xmpp_jid: str | None = None
    xmpp_password: str | None = None


class PrivateUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
