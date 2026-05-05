import secrets
from app.core.config import settings
from app.core.db import supabase


async def create_user_with_xmpp(
    email: str,
    password: str,
    username: str,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict:
    """Crea usuario en Supabase Auth + base_user + cuenta XMPP."""
    from app.services.xmpp import create_xmpp_account

    auth_response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
    })
    user_id = auth_response.user.id

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
        "p_key": settings.XMPP_ENCRYPTION_KEY
    }).execute()

    result = supabase.table("base_user").select("*").eq("id", user_id).execute()
    return result.data[0]


def create_user_simple(email: str, password: str, username: str | None = None) -> dict:
    """Crea usuario sin cuenta XMPP real (para testing/admin)."""
    auth_response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
    })
    user_id = auth_response.user.id
    username = username or email.split("@")[0]
    jid = f"{username}@{settings.XMPP_DOMAIN}"
    dummy_password = secrets.token_urlsafe(16)

    supabase.table("base_user").insert({
        "id": user_id,
        "username": username,
        "email": email,
        "first_name": None,
        "last_name": None,
    }).execute()

    supabase.rpc("insert_xmpp_account", {
        "p_user_id": user_id,
        "p_jid": jid,
        "p_password": dummy_password,
        "p_key": settings.XMPP_ENCRYPTION_KEY
    }).execute()

    result = supabase.table("base_user").select("*").eq("id", user_id).execute()
    return result.data[0]