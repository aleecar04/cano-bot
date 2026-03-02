from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app import crud
from app.api.deps import CurrentUser
from app.core import security
from app.core.config import settings
from app.core.db import supabase
from app.models import Message, NewPassword, Token, UserPublic
from app.utils import generate_password_reset_token, verify_password_reset_token

router = APIRouter(tags=["login"])


@router.post("/login/access-token")
def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.authenticate(email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str) -> Message:
    """
    Password Recovery via Supabase Auth
    """
    try:
        supabase.auth.reset_password_email(email)
    except Exception:
        pass  # Siempre devolvemos el mismo mensaje para evitar email enumeration
    return Message(message="If that email is registered, we sent a password recovery link")


@router.post("/reset-password/")
def reset_password(body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(email=email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    if not user.get("is_active"):
        raise HTTPException(status_code=400, detail="Inactive user")
    try:
        supabase.auth.admin.update_user_by_id(
            user["id"], {"password": body.new_password}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Could not update password")
    return Message(message="Password updated successfully")