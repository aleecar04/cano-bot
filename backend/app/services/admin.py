from app.core.db import supabase
from app.core.errors import not_found
from app.repositories.users import user_repository
from app.repositories.devices import device_repository
from app.repositories.houses import (
    house_repository,
    house_member_repository,
)


def get_stats() -> dict:
    """Aggregate counts visibles en el panel admin."""
    users_count           = user_repository.count_all()
    houses_count          = house_repository.count_all()
    devices_count, online = device_repository.count_with_online()

    return {
        "users":           users_count,
        "houses":          houses_count,
        "devices":         devices_count,
        "devices_online":  online,
        "devices_offline": devices_count - online,
    }


def list_houses() -> dict:
    """All houses with member count, owner info and device count."""
    houses = house_repository.find_all()
    result = []
    for h in houses:
        members = house_member_repository.find_user_role_pairs(h["id"])
        owner_ids = [m["user_id"] for m in members if m["role"] == "owner"]
        owner = None
        if owner_ids:
            u = user_repository.find_by_ids([owner_ids[0]], "username,email")
            owner = u[0] if u else None
        result.append({
            "id":           h["id"],
            "name":         h.get("name"),
            "created_at":   h.get("created_at"),
            "member_count": len(members),
            "device_count": device_repository.count_by_house(h["id"]),
            "owner":        owner,
        })
    return {"data": result, "count": len(result)}


def delete_house(house_id: str) -> None:
    """Delete any house. Cascade borra devices, members, floors/rooms, invitaciones."""
    result = supabase.table("houses").delete().eq("id", house_id).execute()
    if not result.data:
        raise not_found("Casa no encontrada")
