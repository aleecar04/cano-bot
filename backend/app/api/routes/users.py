from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser
from app.api.bot_auth import bot_auth
from app.models.users import (
    RegisterResponse,
    UserProfilePublic,
    UserRegister,
)
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me/profile",
    response_model=UserProfilePublic,
    responses={401: {"description": "Not authenticated"}},
)
def read_user_profile(current_user: CurrentUser) -> Any:
    return user_service.get_profile(current_user)


@router.post(
    "/me/xmpp/regenerate-password",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Cuenta XMPP no encontrada"},
    },
)
async def regenerate_my_xmpp_password(current_user: CurrentUser) -> dict:
    return await user_service.regenerate_xmpp_password(current_user["id"])


@router.post(
    "/signup",
    response_model=RegisterResponse,
    responses={
        400: {"description": "Username already taken"},
    },
)
async def register_user(user_in: UserRegister) -> Any:
    return await user_service.register(user_in)


@router.get("/resolve", responses={401: {"description": "Invalid bot token"}})
def resolve_jid(jid: str, house: dict = Depends(bot_auth)) -> dict:
    return {"user_id": user_service.resolve_jid_in_house(jid, house["id"])}
