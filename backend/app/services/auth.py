"""Authentication: login, password recovery and password reset."""
from app.core.db import supabase
from app.core.errors import bad_request
from app.core.security import verify_password_reset_token
from app.models.auth import Token
from app.repositories.users import user_repository


def login(email: str, password: str) -> Token:
    """Sign in against Supabase Auth and return an access token."""
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email":    email,
            "password": password,
        })
    except Exception:
        raise bad_request("Incorrect email or password")

    if not auth_response.session:
        raise bad_request("Incorrect email or password")

    return Token(access_token=auth_response.session.access_token)


def request_password_recovery(email: str) -> None:
    """Send a password recovery email via Supabase Auth. Silent on failure
    (no se confirma si el email existe)."""
    try:
        supabase.auth.reset_password_email(email)
    except Exception:
        pass


def reset_password(token: str, new_password: str) -> None:
    """Verify a reset token and apply the new password."""
    email = verify_password_reset_token(token=token)
    if not email:
        raise bad_request("Invalid token")
    user = user_repository.find_by_email(email)
    if not user:
        raise bad_request("Invalid token")
    try:
        supabase.auth.admin.update_user_by_id(user["id"], {"password": new_password})
    except Exception:
        raise bad_request("Could not update password")
