import hashlib
import secrets
import string
from datetime import datetime, timezone, timedelta
from app.core.db import supabase
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.repositories.houses import (
    house_repository,
    floor_repository,
    room_repository,
    house_member_repository,
    house_invitation_repository,
)
from app.repositories.users import user_repository


_CODE_CHARS = string.ascii_uppercase + string.digits
_CODE_LEN   = 6
_CODE_TTL_H = 24

_NOT_OWNER_MSG      = "Solo el propietario puede realizar esta acción"
_DEFAULT_HOUSE_NAME = "Mi Casa"


def _generate_bot_token() -> str:
    return secrets.token_urlsafe(32)


def _hash_bot_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_house(name: str, bot_token_hash: str) -> dict:
    return supabase.table("houses").insert({
        "bot_token_hash": bot_token_hash,
        "name":           name,
    }).execute().data[0]


def _add_house_member(house_id: str, user_id: str, role: str, *, idempotent: bool = False) -> None:
    data = {"house_id": house_id, "user_id": user_id, "role": role}
    table = supabase.table("house_members")
    if idempotent:
        table.upsert(data, on_conflict="house_id,user_id").execute()
    else:
        table.insert(data).execute()


def generate_invitation_code(house_id: str, created_by: str) -> str:
    code = "".join(secrets.choice(_CODE_CHARS) for _ in range(_CODE_LEN))
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_CODE_TTL_H)
    supabase.table("house_invitations").insert({
        "house_id":   house_id,
        "code":       code,
        "created_by": created_by,
        "expires_at": expires_at.isoformat(),
    }).execute()
    return code


def consume_invitation_code(code: str, user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    inv = house_invitation_repository.find_unused_by_code(code)
    if not inv:
        raise bad_request("Código inválido o ya utilizado")
    if datetime.fromisoformat(inv["expires_at"]) < now:
        raise bad_request("El código ha caducado")

    house_id = inv["house_id"]
    _add_house_member(house_id, user_id, "member", idempotent=True)

    supabase.table("house_invitations").update({"used_at": now.isoformat()}).eq("id", inv["id"]).execute()

    return house_repository.find_by_id(house_id)


def get_user_house(user_id: str) -> dict | None:
    house_id = house_member_repository.find_house_id_by_user(user_id)
    if not house_id:
        return None
    return house_repository.find_by_id(house_id)


def get_house_id_for_user(user_id: str) -> str | None:
    return house_member_repository.find_house_id_by_user(user_id)


def _bot_resource_from_token_hash(token_hash: str) -> str:
    return f"bot-{token_hash[:12]}"


def get_bot_target_for_user(user_id: str) -> str | None:
    from app.core.config import settings
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return None
    house = house_repository.find_by_id(house_id)
    if not house or not house.get("bot_token_hash"):
        return None
    resource = _bot_resource_from_token_hash(house["bot_token_hash"])
    return f"{settings.XMPP_BOT_JID}/{resource}"


def get_user_role(user_id: str) -> str | None:
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return None
    return house_member_repository.find_role(house_id, user_id)



def require_house(user_id: str) -> str:
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise forbidden("Debes configurar tu casa antes de usar el sistema")
    return house_id


def require_owner(user_id: str) -> None:
    role = get_user_role(user_id)
    if role != "owner":
        raise forbidden(_NOT_OWNER_MSG)


def get_house_member_ids(user_id: str) -> list[str]:
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return [user_id]
    ids = house_member_repository.find_user_ids_by_house(house_id)
    return ids or [user_id]


def get_house_with_detail(user_id: str) -> dict | None:
    house = get_user_house(user_id)
    if not house:
        return None

    floors = _get_floors_by_house(house["id"])
    for floor in floors:
        floor["rooms"] = _get_rooms_by_floor(floor["id"])

    house["floors"] = floors
    return house


def _get_floors_by_house(house_id: str) -> list[dict]:
    return floor_repository.find_by_house(house_id)


def create_floor(house_id: str, name: str) -> dict:
    result = (
        supabase.table("floors")
        .insert(
            {
                "house_id": house_id,
                "name": name,
            }
        )
        .execute()
    )
    return result.data[0]


def _get_rooms_by_floor(floor_id: str) -> list[dict]:
    return room_repository.find_by_floor(floor_id)


def get_rooms_by_house(house_id: str) -> list[dict]:
    floors = _get_floors_by_house(house_id)
    rooms: list[dict] = []
    for floor in floors:
        for room in _get_rooms_by_floor(floor["id"]):
            room["floor_name"] = floor["name"]
            rooms.append(room)
    return rooms


def create_room(floor_id: str, name: str) -> dict:
    result = (
        supabase.table("rooms")
        .insert(
            {
                "floor_id": floor_id,
                "name": name,
            }
        )
        .execute()
    )
    return result.data[0]


def delete_room(user_id: str, floor_id: str, room_id: str) -> None:
    if get_user_role(user_id) != "owner":
        raise forbidden(_NOT_OWNER_MSG)
    supabase.table("rooms").delete().eq("id", room_id).eq("floor_id", floor_id).execute()


def delete_floor(user_id: str, floor_id: str) -> None:
    house = get_user_house(user_id)
    if not house:
        raise not_found("Casa no encontrada")
    if get_user_role(user_id) != "owner":
        raise forbidden(_NOT_OWNER_MSG)
    supabase.table("rooms").delete().eq("floor_id", floor_id).execute()
    supabase.table("floors").delete().eq("id", floor_id).eq("house_id", house["id"]).execute()


def list_house_members(user_id: str) -> list[dict]:
    """Members of the user's house, with usernames. Raises HouseNotFound."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise not_found("Casa no encontrada")
    members = house_member_repository.find_members_by_house(house_id)
    if not members:
        return []
    member_ids = [m["user_id"] for m in members]
    users = user_repository.find_by_ids(member_ids, fields="id, username")
    username_by_id = {u["id"]: u["username"] for u in users}
    return [
        {
            "user_id":    m["user_id"],
            "username":   username_by_id.get(m["user_id"], "—"),
            "role":       m["role"],
            "created_at": m["created_at"],
        }
        for m in members
    ]


def kick_member(owner_id: str, target_user_id: str) -> None:
    if get_user_role(owner_id) != "owner":
        raise forbidden(_NOT_OWNER_MSG)
    if target_user_id == owner_id:
        raise bad_request("No puedes expulsarte a ti mismo. Usa la opción de salir.")
    house_id = get_house_id_for_user(owner_id)
    (
        supabase.table("house_members")
        .delete()
        .eq("house_id", house_id)
        .eq("user_id", target_user_id)
        .execute()
    )


def leave_house(user_id: str) -> None:
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return

    was_owner = get_user_role(user_id) == "owner"
    supabase.table("house_members").delete().eq("house_id", house_id).eq("user_id", user_id).execute()

    remaining = supabase.table("house_members").select("user_id").eq("house_id", house_id).execute().data or []
    if not remaining:
        supabase.table("houses").delete().eq("id", house_id).execute()
        return

    if was_owner:
        new_owner_id = secrets.choice(remaining)["user_id"]
        supabase.table("house_members").update({"role": "owner"}).eq("house_id", house_id).eq("user_id", new_owner_id).execute()


# ── House setup ──────────────────────────────────────────────────────────────
def setup_house(user_id: str, name: str = _DEFAULT_HOUSE_NAME) -> dict:
    if get_house_id_for_user(user_id):
        raise conflict("Ya perteneces a una casa")

    bot_token = _generate_bot_token()
    house = _create_house(name, _hash_bot_token(bot_token))

    try:
        _add_house_member(house["id"], user_id, "owner")
    except Exception:
        try:
            supabase.table("houses").delete().eq("id", house["id"]).execute()
        except Exception:
            pass
        raise

    return {"house_id": house["id"], "bot_token": bot_token}


def regenerate_bot_token(user_id: str) -> str:
    require_owner(user_id)
    house_id = require_house(user_id)

    new_token = _generate_bot_token()
    new_hash  = _hash_bot_token(new_token)

    supabase.table("houses").update({
        "bot_token_hash": new_hash,
        "updated_at":     datetime.now(timezone.utc).isoformat(),
    }).eq("id", house_id).execute()

    return new_token
