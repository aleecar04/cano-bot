from app.core.db import supabase
from app.core.errors import bad_request
from app.core.security import verify_password_reset_token
from app.models.auth import Token
from app.repositories.users import user_repository


def login(email: str, password: str) -> Token:
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email":    email,
            "password": password,
        })
    except Exception:
        raise bad_request("Email o contraseña incorrectos")

    if not auth_response.session:
        raise bad_request("Email o contraseña incorrectos")

    return Token(access_token=auth_response.session.access_token)


def request_password_recovery(email: str) -> None:
    try:
        supabase.auth.reset_password_email(email)
    except Exception:
        pass


def reset_password(token: str, new_password: str) -> None:
    email = verify_password_reset_token(token=token)
    if not email:
        raise bad_request("Token inválido")
    user = user_repository.find_by_email(email)
    if not user:
        raise bad_request("Token inválido")
    try:
        supabase.auth.admin.update_user_by_id(user["id"], {"password": new_password})
    except Exception:
        raise bad_request("No se pudo actualizar la contraseña")
