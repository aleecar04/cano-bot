from supabase import create_client, Client
from app.core.config import settings

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)

def init_db() -> None:
    # Crear superusuario inicial si no existe
    result = supabase.table("base_user").select("*").eq("email", settings.FIRST_SUPERUSER).execute()
    if not result.data:
        supabase.auth.admin.create_user({
            "email": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
            "user_metadata": {"is_superuser": True}
        })