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


# ── Bot token helpers ────────────────────────────────────────────────────────
def _generate_bot_token() -> str:
    """Genera un token opaco de 32 bytes URL-safe (~43 chars)."""
    return secrets.token_urlsafe(32)


def _hash_bot_token(token: str) -> str:
    """Hash SHA-256 hex. Determinístico → permite lookup por hash en BD."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
    inv = house_invitation_repository.find_unused_by_code(code)
    if not inv:
        raise bad_request("Código inválido o ya utilizado")
    if datetime.fromisoformat(inv["expires_at"]) < now:
        raise bad_request("El código ha caducado")

    house_id = inv["house_id"]
    supabase.table("house_members").upsert({
        "house_id": house_id,
        "user_id":  user_id,
        "role":     "member",
    }, on_conflict="house_id,user_id").execute()

    supabase.table("house_invitations").update({"used_at": now.isoformat()}).eq("id", inv["id"]).execute()

    return house_repository.find_by_id(house_id)


def get_user_house(user_id: str) -> dict | None:
    """Find the house the user belongs to via house_members."""
    house_id = house_member_repository.find_house_id_by_user(user_id)
    if not house_id:
        return None
    return house_repository.find_by_id(house_id)


def get_house_id_for_user(user_id: str) -> str | None:
    return house_member_repository.find_house_id_by_user(user_id)


def _bot_resource_from_token_hash(token_hash: str) -> str:
    """Resource XMPP derivado del hash del bot_token. El bot calcula el mismo valor
    con sha256(su_token)[:12], así ambos lados coinciden sin compartir más datos."""
    return f"bot-{token_hash[:12]}"


def get_bot_target_for_user(user_id: str) -> str | None:
    """Return the full XMPP target for routing a message to the user's house bot:
    `<shared_bot_jid>/bot-<first12_of_token_hash>`. Devuelve None si no tiene casa."""
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
    """Return 'owner', 'member', or None if the user has no house."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return None
    return house_member_repository.find_role(house_id, user_id)



def require_house(user_id: str) -> str:
    """Return house_id or raise HouseNotConfigured (403) if user has no house."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise forbidden("Debes configurar tu casa antes de usar el sistema")
    return house_id


def require_owner(user_id: str) -> None:
    """Raise NotOwner if user is not the house owner."""
    role = get_user_role(user_id)
    if role != "owner":
        raise forbidden(_NOT_OWNER_MSG)


def get_house_member_ids(user_id: str) -> list[str]:
    """Return all user_ids that belong to the same house as user_id."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return [user_id]
    ids = house_member_repository.find_user_ids_by_house(house_id)
    return ids or [user_id]


def get_house_with_detail(user_id: str) -> dict | None:
    """Return the user's house with all floors and their rooms nested."""
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
    """Flat list of all rooms in the house (useful for select pickers)."""
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


# ── Floor / room deletion ────────────────────────────────────────────────────
def delete_room(user_id: str, floor_id: str, room_id: str) -> None:
    """Owner-only. Raises NotOwner / RoomNotFound."""
    if get_user_role(user_id) != "owner":
        raise forbidden(_NOT_OWNER_MSG)
    result = supabase.table("rooms").delete().eq("id", room_id).eq("floor_id", floor_id).execute()
    if not result.data:
        raise not_found("Habitación no encontrada")


def delete_floor(user_id: str, floor_id: str) -> None:
    """Owner-only. Cascades rooms first. Raises HouseNotFound / NotOwner / FloorNotFound."""
    house = get_user_house(user_id)
    if not house:
        raise not_found("Casa no encontrada")
    if get_user_role(user_id) != "owner":
        raise forbidden(_NOT_OWNER_MSG)
    supabase.table("rooms").delete().eq("floor_id", floor_id).execute()
    result = supabase.table("floors").delete().eq("id", floor_id).eq("house_id", house["id"]).execute()
    if not result.data:
        raise not_found("Planta no encontrada")


# ── Members ──────────────────────────────────────────────────────────────────
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
    """Owner removes a member from the house.
    Raises NotOwner / CannotKickSelf / MemberNotFound."""
    if get_user_role(owner_id) != "owner":
        raise forbidden(_NOT_OWNER_MSG)
    if target_user_id == owner_id:
        raise bad_request("No puedes expulsarte a ti mismo. Usa la opción de salir.")
    house_id = get_house_id_for_user(owner_id)
    result = (
        supabase.table("house_members")
        .delete()
        .eq("house_id", house_id)
        .eq("user_id", target_user_id)
        .execute()
    )
    if not result.data:
        raise not_found("Usuario no encontrado en la casa")


def leave_house(user_id: str) -> None:
    """Any non-owner member can voluntarily leave the house.
    Raises OwnerCannotLeave / HouseNotFound."""
    role = get_user_role(user_id)
    if role == "owner":
        raise bad_request(
            "El propietario no puede abandonar la casa. Elimínala o transfiere la propiedad."
        )
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise not_found("No perteneces a ninguna casa")
    supabase.table("house_members").delete().eq("house_id", house_id).eq("user_id", user_id).execute()


# ── House setup ──────────────────────────────────────────────────────────────
def setup_house(user_id: str, name: str = _DEFAULT_HOUSE_NAME) -> dict:
    """Create a house, generate a bot_token for it, and add the user as owner.
    Returns {"house_id": str, "bot_token": str} — el bot_token plaintext SOLO se devuelve aquí.
    El servidor solo guarda el hash; si el usuario lo pierde, debe regenerarlo.
    Raises UserAlreadyInHouse."""
    if get_house_id_for_user(user_id):
        raise conflict("Ya perteneces a una casa")

    bot_token = _generate_bot_token()
    bot_token_hash = _hash_bot_token(bot_token)

    house = supabase.table("houses").insert({
        "bot_token_hash": bot_token_hash,
        "name":           name,
    }).execute().data[0]

    try:
        supabase.table("house_members").insert({
            "house_id": house["id"],
            "user_id":  user_id,
            "role":     "owner",
        }).execute()
    except Exception:
        # Rollback: si no se pudo añadir el owner, la house queda huérfana
        # y bloquearía futuros intentos del mismo usuario. La borramos best-effort.
        try:
            supabase.table("houses").delete().eq("id", house["id"]).execute()
        except Exception:
            pass
        raise

    return {"house_id": house["id"], "bot_token": bot_token}


def regenerate_bot_token(user_id: str) -> str:
    """Generate a new bot_token for the user's house. Invalida el anterior.
    Solo el propietario puede hacerlo. Devuelve el token plaintext (una vez).
    Raises HouseNotFound / NotOwner."""
    require_owner(user_id)
    house_id = require_house(user_id)

    new_token = _generate_bot_token()
    new_hash  = _hash_bot_token(new_token)

    supabase.table("houses").update({
        "bot_token_hash": new_hash,
        "updated_at":     datetime.now(timezone.utc).isoformat(),
    }).eq("id", house_id).execute()

    return new_token
