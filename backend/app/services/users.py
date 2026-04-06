import secrets
from fastapi import HTTPException
from app.core.config import settings
from app.core.db import supabase


async def create_user_with_xmpp(email: str, password: str, username: str) -> dict:
    """Crea usuario en Supabase Auth + base_user + cuenta XMPP."""
    auth_response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
    })
    user_id = auth_response.user.id

    from app.services.xmpp import create_xmpp_account
    xmpp_password = await create_xmpp_account(username=username)

    result = supabase.table("base_user").insert({
        "id": user_id,
        "username": username,
        "jid": f"{username}@{settings.XMPP_DOMAIN}",
        "xmpp_password": xmpp_password,
    }).execute()

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

    result = supabase.table("base_user").insert({
        "id": user_id,
        "username": username,
        "jid": f"{username}@{settings.XMPP_DOMAIN}",
        "xmpp_password": secrets.token_urlsafe(16),
    }).execute()

    return result.data[0]