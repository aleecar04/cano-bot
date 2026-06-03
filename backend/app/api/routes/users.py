import uuid
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_current_active_superuser
from app.api.bot_auth import bot_auth
from app.models.common import Message
from app.models.users import (
    BaseUserPublic,
    UpdatePassword,
    UserCreate,
    UserProfilePublic,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not enough privileges"},
    },
)
def read_users(skip: int = 0, limit: int = 100) -> Any:
    page = user_service.list_users(skip=skip, limit=limit)
    return UsersPublic(data=page["data"], count=page["count"])


@router.post(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
    responses={
        400: {"description": "A user with this email already exists"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not enough privileges"},
    },
)
def create_user(*, user_in: UserCreate) -> Any:
    return user_service.create_user_for_admin(user_in)


@router.patch(
    "/me",
    response_model=UserPublic,
    responses={
        409: {"description": "User with this email already exists"},
    },
)
def update_user_me(*, user_in: UserUpdateMe, current_user: CurrentUser) -> Any:
    return user_service.update_me(current_user["id"], user_in)


@router.patch(
    "/me/password",
    response_model=Message,
    responses={
        400: {"description": "New password is the same as current / Incorrect current password / Could not update password"},
    },
)
def update_password_me(*, body: UpdatePassword, current_user: CurrentUser) -> Any:
    user_service.change_password_me(
        email=current_user["email"],
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return Message(message="Password updated successfully")


@router.get(
    "/me",
    response_model=UserPublic,
    responses={401: {"description": "Not authenticated"}},
)
def read_user_me(current_user: CurrentUser) -> Any:
    return current_user


@router.get(
    "/me/profile",
    response_model=UserProfilePublic,
    responses={401: {"description": "Not authenticated"}},
)
def read_user_profile(current_user: CurrentUser) -> Any:
    return user_service.get_profile(current_user)


@router.delete(
    "/me",
    response_model=Message,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Super users are not allowed to delete themselves"},
    },
)
def delete_user_me(current_user: CurrentUser) -> Any:
    user_service.delete_me(current_user)
    return Message(message="User deleted successfully")


@router.post(
    "/signup",
    response_model=BaseUserPublic,
    responses={
        400: {"description": "Username already taken"},
    },
)
async def register_user(user_in: UserRegister) -> Any:
    return await user_service.register(user_in)


@router.get("/resolve", responses={401: {"description": "Invalid bot token"}})
def resolve_jid(jid: str, house: dict = Depends(bot_auth)) -> dict:
    """Bot-only: resuelve un JID a user_id SOLO si ese usuario es miembro de la casa
    del bot. Devuelve {user_id: str|None}. Combina resolución + control de acceso."""
    return {"user_id": user_service.resolve_jid_in_house(jid, house["id"])}


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not enough privileges"},
        404: {"description": "User not found"},
    },
)
def read_user_by_id(user_id: uuid.UUID, current_user: CurrentUser) -> Any:
    return user_service.get_user_by_id(str(user_id), current_user)


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not enough privileges"},
        404: {"description": "User not found"},
        409: {"description": "User with this email already exists"},
    },
)
def update_user(*, user_id: uuid.UUID, user_in: UserUpdate) -> Any:
    return user_service.admin_update_user(str(user_id), user_in)


@router.delete(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Super users are not allowed to delete themselves"},
        404: {"description": "User not found"},
    },
)
def delete_user(current_user: CurrentUser, user_id: uuid.UUID) -> Message:
    user_service.admin_delete_user(str(user_id), current_user)
    return Message(message="User deleted successfully")
