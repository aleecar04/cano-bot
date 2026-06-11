import secrets

from app.core.config import settings
from app.core.db import supabase
from app.core.errors import bad_request, not_found
from app.models.users import UserRegister
from app.repositories.houses import house_member_repository
from app.repositories.users import user_repository, xmpp_account_repository
from app.services.xmpp import change_xmpp_password, create_xmpp_account


def get_user_by_email(email: str) -> dict | None:
    return user_repository.find_by_email(email)


def resolve_jid_in_house(jid: str, house_id: str) -> str | None:
    user_id = xmpp_account_repository.find_user_id_by_jid(jid)
    if not user_id:
        return None
    if house_member_repository.find_house_id_by_user(user_id) != house_id:
        return None
    return user_id


def resolve_username_to_email(username: str) -> str:
    email = user_repository.find_email_by_username(username)
    if not email:
        raise not_found("Usuario no encontrado")
    return email


async def create_user_with_xmpp(
    email: str,
    password: str,
    username: str,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict:
    auth_response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
    })
    user_id = auth_response.user.id

    try:
        xmpp_password = await create_xmpp_account(username=username)
        jid = f"{username}@{settings.XMPP_DOMAIN}"

        supabase.table("base_user").insert({
            "id": user_id,
            "username": username,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }).execute()

        supabase.rpc("insert_xmpp_account", {
            "p_user_id": user_id,
            "p_jid": jid,
            "p_password": xmpp_password,
            "p_key": settings.XMPP_ENCRYPTION_KEY,
        }).execute()
    except Exception:
        try:
            supabase.table("base_user").delete().eq("id", user_id).execute()
        except Exception:
            pass
        try:
            supabase.auth.admin.delete_user(user_id)
        except Exception:
            pass
        raise

    user = user_repository.find_by_id(user_id) or {}
    return {**user, "xmpp_jid": jid, "xmpp_password": xmpp_password}


async def register(user_in: UserRegister) -> dict:
    if user_repository.exists_by_username(user_in.username):
        raise bad_request("El nombre de usuario ya está en uso")
    return await create_user_with_xmpp(
        email=user_in.email,
        password=user_in.password,
        username=user_in.username,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
    )


def get_profile(current_user: dict) -> dict:
    user_id = current_user["id"]

    row = user_repository.find_basic_by_id(user_id) or {}
    jid = xmpp_account_repository.find_jid_by_user(user_id)

    first = row.get("first_name") or ""
    last = row.get("last_name") or ""
    full = f"{first} {last}".strip() or None

    return {
        "id":            current_user["id"],
        "email":         current_user.get("email"),
        "is_active":     current_user.get("is_active"),
        "full_name":    full,
        "created_at":   current_user.get("created_at"),
        "username":     row.get("username"),
        "first_name":   row.get("first_name"),
        "last_name":    row.get("last_name"),
        "xmpp_jid":     jid,
    }


async def regenerate_xmpp_password(user_id: str) -> dict:
    jid = xmpp_account_repository.find_jid_by_user(user_id)
    if not jid:
        raise not_found("Cuenta XMPP no encontrada")
    new_password = secrets.token_urlsafe(16)
    await change_xmpp_password(jid, new_password)
    supabase.rpc("update_xmpp_password", {
        "p_user_id":  user_id,
        "p_password": new_password,
        "p_key":      settings.XMPP_ENCRYPTION_KEY,
    }).execute()
    return {"xmpp_jid": jid, "xmpp_password": new_password}
