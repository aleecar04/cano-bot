from app.core.db import supabase
from app.models import FavoriteActionCreate
from app.services.command_executor import execute_command, CommandSource

MAX_FAVORITES = 4


def get_favorites(user_id: str) -> list[dict]:
    result = supabase.table("favorite_actions")\
        .select("*, devices(name, type)")\
        .eq("user_id", user_id)\
        .order("position")\
        .execute()
    return result.data or []


def add_favorite(fav_in: FavoriteActionCreate, user_id: str) -> dict:
    existing = get_favorites(user_id)
    if len(existing) >= MAX_FAVORITES:
        raise ValueError(f"Solo puedes tener {MAX_FAVORITES} acciones favoritas")

    position = len(existing)
    result = supabase.table("favorite_actions").insert({
        "user_id":   user_id,
        "device_id": str(fav_in.device_id),
        "action":    fav_in.action,
        "payload":   fav_in.payload,
        "label":     fav_in.label,
        "position":  position,
    }).execute()

    if not result.data:
        raise RuntimeError("Error al guardar favorito")
    return result.data[0]


async def execute_favorite(favorite_id: str, user_id: str) -> dict:
    result = supabase.table("favorite_actions")\
        .select("*")\
        .eq("id", favorite_id)\
        .eq("user_id", user_id)\
        .execute()
    if not result.data:
        raise ValueError("Favorito no encontrado")
    fav = result.data[0]
    return await execute_command(
        device_id=fav["device_id"],
        action=fav["action"],
        payload=fav.get("payload", {}),
        user_id=user_id,
        source=CommandSource(source_type="favorite", source_id=favorite_id),
    )


def delete_favorite(favorite_id: str, user_id: str) -> bool:
    result = supabase.table("favorite_actions")\
        .delete()\
        .eq("id", favorite_id)\
        .eq("user_id", user_id)\
        .execute()
    return bool(result.data)
