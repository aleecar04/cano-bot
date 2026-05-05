import secrets
import string
from datetime import datetime, timezone, timedelta
from app.core.db import supabase


_CODE_CHARS = string.ascii_uppercase + string.digits
_CODE_LEN   = 6
_CODE_TTL_H = 24


def generate_invitation_code(house_id: str, created_by: str) -> str:
    """Generate a 6-char invitation code valid for 24 hours."""
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
    """Validate code, add user to house_members, mark code as used. Returns the house."""
    now = datetime.now(timezone.utc)
    result = (
        supabase.table("house_invitations")
        .select("*")
        .eq("code", code.upper())
        .is_("used_at", "null")
        .execute()
    )
    if not result.data:
        raise ValueError("Código inválido o ya utilizado")
    inv = result.data[0]
    if datetime.fromisoformat(inv["expires_at"]) < now:
        raise ValueError("El código ha caducado")

    house_id = inv["house_id"]
    supabase.table("house_members").upsert({
        "house_id": house_id,
        "user_id":  user_id,
        "role":     "member",
    }, on_conflict="house_id,user_id").execute()

    supabase.table("house_invitations").update({"used_at": now.isoformat()}).eq("id", inv["id"]).execute()

    house = supabase.table("houses").select("*").eq("id", house_id).execute()
    return house.data[0]


def get_user_house(user_id: str) -> dict | None:
    """Find the house the user belongs to via house_members."""
    member = supabase.table("house_members").select("house_id").eq("user_id", user_id).execute()
    if not member.data:
        return None
    house_id = member.data[0]["house_id"]
    result = supabase.table("houses").select("*").eq("id", house_id).execute()
    return result.data[0] if result.data else None


def get_house_id_for_user(user_id: str) -> str | None:
    house = get_user_house(user_id)
    return house["id"] if house else None


def get_bot_jid_for_user(user_id: str) -> str | None:
    """Return the bot_jid of the house the user belongs to — single JOIN query."""
    result = (
        supabase.table("house_members")
        .select("houses!inner(bot_jid)")
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]["houses"].get("bot_jid")


def get_user_role(user_id: str) -> str | None:
    """Return 'owner', 'member', or None if the user has no house."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return None
    result = supabase.table("house_members").select("role").eq("house_id", house_id).eq("user_id", user_id).execute()
    return result.data[0]["role"] if result.data else None



def require_house(user_id: str) -> str:
    """Return house_id or raise ValueError if user has no house."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise ValueError("Debes configurar tu casa antes de usar el sistema")
    return house_id


def require_owner(user_id: str) -> None:
    """Raise ValueError if user is not the house owner."""
    role = get_user_role(user_id)
    if role != "owner":
        raise ValueError("Solo el propietario puede realizar esta acción")


def get_house_member_ids(user_id: str) -> list[str]:
    """Return all user_ids that belong to the same house as user_id."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return [user_id]
    result = supabase.table("house_members").select("user_id").eq("house_id", house_id).execute()
    return [m["user_id"] for m in result.data] if result.data else [user_id]


def create_user_house(user_id: str, name: str | None = None) -> dict:
    result = (
        supabase.table("houses")
        .insert(
            {
                "user_id": user_id,
                "name": name or "Mi Casa",
            }
        )
        .execute()
    )
    return result.data[0]


def get_house_with_detail(user_id: str) -> dict | None:
    """Return the user's house with all floors and their rooms nested."""
    house = get_user_house(user_id)
    if not house:
        return None

    floors = get_floors_by_house(house["id"])
    for floor in floors:
        floor["rooms"] = get_rooms_by_floor(floor["id"])

    house["floors"] = floors
    return house


def get_floors_by_house(house_id: str) -> list[dict]:
    result = (
        supabase.table("floors")
        .select("*")
        .eq("house_id", house_id)
        .order("level")
        .execute()
    )
    return result.data or []


def create_floor(house_id: str, name: str, level: int = 0) -> dict:
    result = (
        supabase.table("floors")
        .insert(
            {
                "house_id": house_id,
                "name": name,
                "level": level,
            }
        )
        .execute()
    )
    return result.data[0]


def get_rooms_by_floor(floor_id: str) -> list[dict]:
    result = supabase.table("rooms").select("*").eq("floor_id", floor_id).execute()
    return result.data or []


def get_rooms_by_house(house_id: str) -> list[dict]:
    """Flat list of all rooms in the house (useful for select pickers)."""
    floors = get_floors_by_house(house_id)
    rooms: list[dict] = []
    for floor in floors:
        for room in get_rooms_by_floor(floor["id"]):
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
