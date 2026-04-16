import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app import crud
from app.api.deps import CurrentUser, get_current_active_superuser
from app.api.routes.messages import verify_webhook_secret
from app.core.db import supabase
from app.models import (
    Message,
    UpdatePassword,
    UserCreate,
    UserProfilePublic,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
    BaseUserPublic,
)
from app.services.users import create_user_simple, create_user_with_xmpp

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
    result = supabase.table("base_user").select("*", count="exact").range(skip, skip + limit - 1).order("created_at", desc=True).execute()
    return UsersPublic(data=result.data, count=result.count)


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
async def create_user(*, user_in: UserCreate) -> Any:
    if crud.get_user_by_email(email=user_in.email):
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system.")
    return await create_user_simple(email=user_in.email, password=user_in.password)


@router.patch(
    "/me",
    response_model=UserPublic,
    responses={
        409: {"description": "User with this email already exists"},
    },
)
def update_user_me(*, user_in: UserUpdateMe, current_user: CurrentUser) -> Any:
    if user_in.email:
        existing_user = crud.get_user_by_email(email=user_in.email)
        if existing_user and existing_user["id"] != current_user["id"]:
            raise HTTPException(status_code=409, detail="User with this email already exists")
    user_data = user_in.model_dump(exclude_unset=True)
    result = supabase.table("base_user").update(user_data).eq("id", current_user["id"]).execute()
    return result.data[0]


@router.patch(
    "/me/password",
    response_model=Message,
    responses={
        400: {"description": "New password is the same as current / Incorrect current password / Could not update password"},
    },
)
def update_password_me(*, body: UpdatePassword, current_user: CurrentUser) -> Any:
    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail="New password cannot be the same as the current one")
    try:
        supabase.auth.sign_in_with_password({
            "email": current_user["email"],
            "password": body.current_password,
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Incorrect current password")
    try:
        supabase.auth.update_user({"password": body.new_password})
    except Exception:
        raise HTTPException(status_code=400, detail="Could not update password")
    return Message(message="Password updated successfully")


@router.get(
    "/me",
    response_model=UserPublic,
    responses={
        401: {"description": "Not authenticated"},
    },
)
def read_user_me(current_user: CurrentUser) -> Any:
    return current_user


@router.get(
    "/me/profile",
    response_model=UserProfilePublic,
    responses={
        401: {"description": "Not authenticated"},
    },
)
def read_user_profile(current_user: CurrentUser) -> Any:
    user_id = current_user["id"]

    base = supabase.table("base_user").select("username,first_name,last_name").eq("id", user_id).execute()
    row = base.data[0] if base.data else {}

    xmpp = supabase.table("xmpp_accounts").select("jid").eq("user_id", user_id).execute()
    jid = xmpp.data[0]["jid"] if xmpp.data else None

    first = row.get("first_name") or ""
    last = row.get("last_name") or ""
    full = f"{first} {last}".strip() or None

    return UserProfilePublic(
        id=current_user["id"],
        email=current_user.get("email"),
        is_active=current_user.get("is_active"),
        is_superuser=current_user.get("is_superuser"),
        full_name=full,
        created_at=current_user.get("created_at"),
        username=row.get("username"),
        first_name=row.get("first_name"),
        last_name=row.get("last_name"),
        xmpp_jid=jid,
    )


@router.delete(
    "/me",
    response_model=Message,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Super users are not allowed to delete themselves"},
    },
)
def delete_user_me(current_user: CurrentUser) -> Any:
    if current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Super users are not allowed to delete themselves")
    supabase.table("base_user").delete().eq("id", current_user["id"]).execute()
    return Message(message="User deleted successfully")


@router.post(
    "/signup",
    response_model=BaseUserPublic,
    responses={
        400: {"description": "Username already taken"},
    },
)
async def register_user(user_in: UserRegister) -> Any:
    if supabase.table("base_user").select("id").eq("username", user_in.username).execute().data:
        raise HTTPException(status_code=400, detail="Username already taken")
    return await create_user_with_xmpp(
        email=user_in.email,
        password=user_in.password,
        username=user_in.username,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
    )


@router.get(
    "/by-jid/{jid}",
    dependencies=[Depends(verify_webhook_secret)],
    responses={
        401: {"description": "Invalid webhook token"},
        404: {"description": "JID not found"},
    },
)
def get_user_id_by_jid(jid: str) -> dict:
    """Bot-only endpoint: resolve an XMPP JID to an app user_id."""
    result = supabase.table("xmpp_accounts").select("user_id").eq("jid", jid).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"JID '{jid}' not found")
    return {"user_id": result.data[0]["user_id"]}


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
    result = supabase.table("base_user").select("*").eq("id", str(user_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = result.data[0]
    if user["id"] != current_user["id"] and not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    return user


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
    result = supabase.table("base_user").select("*").eq("id", str(user_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="The user with this id does not exist in the system")
    if user_in.email:
        existing_user = crud.get_user_by_email(email=user_in.email)
        if existing_user and existing_user["id"] != str(user_id):
            raise HTTPException(status_code=409, detail="User with this email already exists")
    return crud.update_user(user_id=user_id, user_in=user_in)


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
    result = supabase.table("base_user").select("*").eq("id", str(user_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    if result.data[0]["id"] == current_user["id"]:
        raise HTTPException(status_code=403, detail="Super users are not allowed to delete themselves")
    supabase.table("base_user").delete().eq("id", str(user_id)).execute()
    return Message(message="User deleted successfully")