from fastapi import APIRouter, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from fastapi import Depends
from app.core.db import supabase
from app.models import Message, NewPassword, Token, UserPublic
from app.core.security import create_password_reset_token, verify_password_reset_token
from app.api.deps import CurrentUser

router = APIRouter(tags=["login"])


@router.post(
    "/login/access-token",
    responses={
        400: {"description": "Incorrect email or password"},
    },
)
def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": form_data.username,
            "password": form_data.password,
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not auth_response.session:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    user_id = auth_response.session.user.id
    row = supabase.table("base_user").select("email_verified").eq("id", user_id).execute()
    if row.data and not row.data[0].get("email_verified", False):
        raise HTTPException(status_code=403, detail="Debes verificar tu correo antes de iniciar sesión")

    return Token(access_token=auth_response.session.access_token)


@router.post(
    "/login/test-token",
    response_model=UserPublic,
    responses={
        401: {"description": "Not authenticated"},
    },
)
def test_token(current_user: CurrentUser):
    return current_user


@router.post(
    "/password-recovery/{email}",
    responses={
        200: {"description": "Recovery email sent if the address is registered"},
    },
)
def recover_password(email: str) -> Message:
    try:
        supabase.auth.reset_password_email(email)
    except Exception:
        pass
    return Message(message="If that email is registered, we sent a password recovery link")


@router.post(
    "/reset-password/",
    responses={
        400: {"description": "Invalid token / User not found / Could not update password"},
    },
)
def reset_password(body: NewPassword) -> Message:
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    try:
        result = supabase.table("user").select("id").eq("email", email).execute()
        if not result.data:
            raise HTTPException(status_code=400, detail="Invalid token")
        user_id = result.data[0]["id"]
        supabase.auth.admin.update_user_by_id(user_id, {"password": body.new_password})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Could not update password")
    return Message(message="Password updated successfully")