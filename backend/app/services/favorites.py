from fastapi import HTTPException, status

from app.core.db import supabase
from app.core.errors import bad_request, not_found
from app.models.favorites import FavoriteActionCreate
from app.services.command_executor import execute_command, CommandSource
from app.repositories.favorites import favorite_repository

MAX_FAVORITES = 6


def get_favorites(user_id: str) -> list[dict]:
    return favorite_repository.find_by_user(user_id)


def add_favorite(fav_in: FavoriteActionCreate, user_id: str) -> dict:
    existing = get_favorites(user_id)
    if len(existing) >= MAX_FAVORITES:
        raise bad_request(f"Solo puedes tener {MAX_FAVORITES} acciones favoritas")

    data = fav_in.model_dump(mode="json")
    data["user_id"] = user_id
    result = supabase.table("favorite_actions").insert(data).execute()

    if not result.data:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error al guardar favorito")
    return result.data[0]


async def execute_favorite(favorite_id: str, user_id: str) -> dict:
    fav = favorite_repository.find_by_id_and_user(favorite_id, user_id)
    if not fav:
        raise not_found("Favorito no encontrado")
    return await execute_command(
        device_id=fav["device_id"],
        action=fav["action"],
        payload=fav.get("payload", {}),
        user_id=user_id,
        source=CommandSource(source_type="favorite", source_id=favorite_id),
    )


def update_favorite(favorite_id: str, user_id: str, action: str, payload: dict, label: str | None) -> dict | None:
    result = supabase.table("favorite_actions")\
        .update({"action": action, "payload": payload, "label": label})\
        .eq("id", favorite_id)\
        .eq("user_id", user_id)\
        .execute()
    return result.data[0] if result.data else None


def delete_favorite(favorite_id: str, user_id: str) -> bool:
    result = supabase.table("favorite_actions")\
        .delete()\
        .eq("id", favorite_id)\
        .eq("user_id", user_id)\
        .execute()
    return bool(result.data)
