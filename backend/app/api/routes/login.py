from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from app.api.deps import CurrentUser
from app.models.auth import NewPassword, Token
from app.models.common import Message
from app.models.users import UserPublic
from app.services.auth import auth_service
from app.services.users import users_service as user_service

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
    return auth_service.login(form_data.username, form_data.password)


@router.get("/auth/resolve-username/{username}")
def resolve_username(username: str):
    return {"email": user_service.resolve_username_to_email(username)}


@router.post(
    "/login/test-token",
    response_model=UserPublic,
    responses={401: {"description": "Not authenticated"}},
)
def test_token(current_user: CurrentUser):
    return current_user


@router.post(
    "/password-recovery/{email}",
    responses={200: {"description": "Recovery email sent if the address is registered"}},
)
def recover_password(email: str) -> Message:
    auth_service.request_password_recovery(email)
    return Message(message="If that email is registered, we sent a password recovery link")


@router.post(
    "/reset-password/",
    responses={400: {"description": "Invalid token / User not found / Could not update password"}},
)
def reset_password(body: NewPassword) -> Message:
    auth_service.reset_password(body.token, body.new_password)
    return Message(message="Password updated successfully")
