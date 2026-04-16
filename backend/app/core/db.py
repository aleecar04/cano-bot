import secrets
from supabase import create_client, Client
from app.core.config import settings

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)

def init_db() -> None:
    result = supabase.table("base_user").select("*").eq("email", settings.FIRST_SUPERUSER).execute()
    if not result.data:
        auth_response = supabase.auth.admin.create_user({
            "email": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
            "email_confirm": True,
        })
        user_id = auth_response.user.id
        username = settings.FIRST_SUPERUSER.split("@")[0]
        
        supabase.table("base_user").insert({
            "id": user_id,
            "username": username,
            "email": settings.FIRST_SUPERUSER,
            "is_active": True,
            "is_superuser": True,
        }).execute()
        
        jid = f"{username}@{settings.XMPP_DOMAIN}"
        dummy_password = secrets.token_urlsafe(16)
        supabase.rpc("insert_xmpp_account", {
            "p_user_id": user_id,
            "p_jid": jid,
            "p_password": dummy_password,
            "p_key": settings.XMPP_ENCRYPTION_KEY
        }).execute()