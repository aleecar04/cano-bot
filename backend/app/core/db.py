from supabase import create_client, Client
from app.core.config import settings

# Cliente único de Supabase. Lo importan todos los services y queries del backend
# para hablar con la BD (SELECT / INSERT / UPDATE / DELETE / RPC).
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY,
)
