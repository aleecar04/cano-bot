from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.api.deps import CurrentUser
from app.api.routes.messages import verify_webhook_secret
from app.models import HousePublic, FloorPublic, RoomPublic, FloorCreate, RoomCreate, CommandCreate, ScheduleCreate, GroupScheduleCreate
from app.services import home as home_service
from app.services import devices as device_service
from app.services import schedules as schedule_service
from app.core.db import supabase

router = APIRouter(prefix="/houses", tags=["houses"])


@router.get("/me", response_model=HousePublic)
def get_my_house(current_user: CurrentUser):
    house = home_service.get_house_with_detail(current_user["id"])
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    return house


@router.get("/me/rooms", response_model=list[RoomPublic])
def get_my_rooms(current_user: CurrentUser):
    """Flat list of all rooms — used for device-assignment selects."""
    house = home_service.get_user_house(current_user["id"])
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    return home_service.get_rooms_by_house(house["id"])


def _check_owner(user_id: str):
    try:
        home_service.require_owner(user_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/me/floors", response_model=FloorPublic, status_code=201)
def add_floor(floor_in: FloorCreate, current_user: CurrentUser):
    house = home_service.get_user_house(current_user["id"])
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    _check_owner(current_user["id"])
    try:
        floor = home_service.create_floor(house["id"], floor_in.name, floor_in.level)
    except Exception:
        raise HTTPException(status_code=409, detail="Ya existe una planta con ese nombre")
    floor["rooms"] = []
    return floor


@router.post("/floors/{floor_id}/rooms", response_model=RoomPublic, status_code=201)
def add_room(floor_id: str, room_in: RoomCreate, current_user: CurrentUser):
    _check_owner(current_user["id"])
    try:
        room = home_service.create_room(floor_id, room_in.name)
    except Exception:
        raise HTTPException(status_code=409, detail="Ya existe una habitación con ese nombre en esta planta")
    return room


@router.delete("/floors/{floor_id}/rooms/{room_id}", status_code=204)
def delete_room(floor_id: str, room_id: str, current_user: CurrentUser):
    _check_owner(current_user["id"])
    result = supabase.table("rooms").delete().eq("id", room_id).eq("floor_id", floor_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")


@router.delete("/floors/{floor_id}", status_code=204)
def delete_floor(floor_id: str, current_user: CurrentUser):
    house = home_service.get_user_house(current_user["id"])
    if not house:
        raise HTTPException(status_code=404, detail="Casa no encontrada")
    _check_owner(current_user["id"])
    supabase.table("rooms").delete().eq("floor_id", floor_id).execute()
    result = supabase.table("floors").delete().eq("id", floor_id).eq("house_id", house["id"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Planta no encontrada")


# ── Group actions ────────────────────────────────────────────────────────────

class GroupActionRequest(BaseModel):
    action: str  # only "encender" or "apagar"


@router.post("/rooms/{room_id}/action")
async def room_action(room_id: str, body: GroupActionRequest, current_user: CurrentUser):
    if body.action not in ("encender", "apagar"):
        raise HTTPException(status_code=400, detail="Solo se permiten acciones 'encender' o 'apagar'")
    devices = supabase.table("devices").select("id").eq("room_id", room_id).execute().data or []
    if not devices:
        raise HTTPException(status_code=404, detail="No hay dispositivos en esta habitación")
    cmd_in = CommandCreate(accion=body.action, payload={})
    results = []
    for d in devices:
        try:
            r = await device_service.send_command(d["id"], cmd_in, current_user["id"])
            results.append({"device_id": d["id"], "command_id": r["command_id"]})
        except Exception:
            results.append({"device_id": d["id"], "error": "No se pudo enviar"})
    return {"ok": True, "results": results}


@router.post("/floors/{floor_id}/action")
async def floor_action(floor_id: str, body: GroupActionRequest, current_user: CurrentUser):
    if body.action not in ("encender", "apagar"):
        raise HTTPException(status_code=400, detail="Solo se permiten acciones 'encender' o 'apagar'")
    rooms = supabase.table("rooms").select("id").eq("floor_id", floor_id).execute().data or []
    room_ids = [r["id"] for r in rooms]
    if not room_ids:
        raise HTTPException(status_code=404, detail="No hay habitaciones en esta planta")
    devices = supabase.table("devices").select("id").in_("room_id", room_ids).execute().data or []
    if not devices:
        raise HTTPException(status_code=404, detail="No hay dispositivos en esta planta")
    cmd_in = CommandCreate(accion=body.action, payload={})
    results = []
    for d in devices:
        try:
            r = await device_service.send_command(d["id"], cmd_in, current_user["id"])
            results.append({"device_id": d["id"], "command_id": r["command_id"]})
        except Exception:
            results.append({"device_id": d["id"], "error": "No se pudo enviar"})
    return {"ok": True, "results": results}


# ── Group schedules ──────────────────────────────────────────────────────────

@router.post("/rooms/{room_id}/schedule")
def room_schedule(room_id: str, schedule_in: GroupScheduleCreate, current_user: CurrentUser):
    """Create a schedule for every device in a room."""
    devices = supabase.table("devices").select("id,name").eq("room_id", room_id).execute().data or []
    if not devices:
        raise HTTPException(status_code=404, detail="No hay dispositivos en esta habitación")
    created = 0
    for d in devices:
        try:
            data = schedule_in.model_dump()
            data["name"] = f"{schedule_in.name}: {d.get('name', d['id'])}"
            s = ScheduleCreate(**data, device_id=d["id"])
            schedule_service.create_schedule(s, current_user["id"])
            created += 1
        except ValueError:
            pass  # skip conflicting schedules silently
    return {"ok": True, "created": created}


@router.post("/floors/{floor_id}/schedule")
def floor_schedule(floor_id: str, schedule_in: GroupScheduleCreate, current_user: CurrentUser):
    """Create a schedule for every device in a floor."""
    rooms = supabase.table("rooms").select("id").eq("floor_id", floor_id).execute().data or []
    room_ids = [r["id"] for r in rooms]
    if not room_ids:
        raise HTTPException(status_code=404, detail="No hay habitaciones en esta planta")
    devices = supabase.table("devices").select("id,name").in_("room_id", room_ids).execute().data or []
    if not devices:
        raise HTTPException(status_code=404, detail="No hay dispositivos en esta planta")
    created = 0
    for d in devices:
        try:
            data = schedule_in.model_dump()
            data["name"] = f"{schedule_in.name}: {d.get('name', d['id'])}"
            s = ScheduleCreate(**data, device_id=d["id"])
            schedule_service.create_schedule(s, current_user["id"])
            created += 1
        except ValueError:
            pass
    return {"ok": True, "created": created}


# ── House members ─────────────────────────────────────────────────────────────

@router.get("/member-check", dependencies=[Depends(verify_webhook_secret)])
def member_check(user_id: str):
    """Bot-only: check if a user_id belongs to any house."""
    result = supabase.table("house_members").select("house_id").eq("user_id", user_id).execute()
    return {"is_member": bool(result.data)}


@router.get("/me/members")
def get_members(current_user: CurrentUser):
    house_id = home_service.get_house_id_for_user(current_user["id"])
    if not house_id:
        raise HTTPException(status_code=404, detail="Casa no encontrada")
    members = supabase.table("house_members").select("user_id, role, created_at").eq("house_id", house_id).execute()
    result = []
    for m in (members.data or []):
        user = supabase.table("base_user").select("username").eq("id", m["user_id"]).execute()
        result.append({
            "user_id": m["user_id"],
            "username": user.data[0]["username"] if user.data else "—",
            "role": m["role"],
            "created_at": m["created_at"],
        })
    return result


# ── Invitation codes ──────────────────────────────────────────────────────────

class InviteCodeResponse(BaseModel):
    code: str
    expires_in_hours: int = 24


class JoinRequest(BaseModel):
    code: str


@router.post("/me/invite", response_model=InviteCodeResponse)
def generate_invite(current_user: CurrentUser):
    house = home_service.get_user_house(current_user["id"])
    if not house:
        raise HTTPException(status_code=404, detail="No tienes una casa asignada")
    code = home_service.generate_invitation_code(house["id"], current_user["id"])
    return {"code": code, "expires_in_hours": 24}


@router.post("/join", status_code=200)
def join_house(body: JoinRequest, current_user: CurrentUser):
    try:
        house = home_service.consume_invitation_code(body.code, current_user["id"])
        return {"ok": True, "house_id": house["id"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Member management ────────────────────────────────────────────────────────

@router.delete("/me/members/{user_id}", status_code=204)
def kick_member(user_id: str, current_user: CurrentUser):
    """Owner removes a member from the house."""
    try:
        home_service.require_owner(current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    house_id = home_service.get_house_id_for_user(current_user["id"])
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="No puedes expulsarte a ti mismo. Usa la opción de salir.")
    result = supabase.table("house_members").delete().eq("house_id", house_id).eq("user_id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado en la casa")


@router.delete("/me/leave", status_code=204)
def leave_house(current_user: CurrentUser):
    """Any member can voluntarily leave the house."""
    user_id = current_user["id"]
    role = home_service.get_user_role(user_id)
    if role == "owner":
        raise HTTPException(status_code=400, detail="El propietario no puede abandonar la casa. Elimínala o transfiere la propiedad.")
    house_id = home_service.get_house_id_for_user(user_id)
    if not house_id:
        raise HTTPException(status_code=404, detail="No perteneces a ninguna casa")
    supabase.table("house_members").delete().eq("house_id", house_id).eq("user_id", user_id).execute()


# ── House setup (owner creates house by providing valid bot JID) ──────────────

class HouseSetupRequest(BaseModel):
    bot_jid: str


@router.post("/setup", status_code=200)
def setup_house(body: HouseSetupRequest, current_user: CurrentUser):
    """
    Owner flow: create the house when the user provides a valid bot JID.
    Validates:
      0. User not already in a house
      1. JID does not belong to a system user (xmpp_accounts)
      2. JID not already assigned to another house
    Then: creates house + assigns bot_jid + adds user as owner.
    """
    # 0. User must not already have a house
    if home_service.get_house_id_for_user(current_user["id"]):
        raise HTTPException(status_code=409, detail="Ya perteneces a una casa")

    bot_jid = body.bot_jid.strip().lower()

    # 1. Bot JID must not be a registered user's JID
    user_jid = supabase.table("xmpp_accounts").select("id").eq("jid", bot_jid).execute()
    if user_jid.data:
        raise HTTPException(status_code=400, detail="Ese JID pertenece a un usuario del sistema, no a un bot")

    # 2. Bot JID must not already be assigned to another house
    existing = supabase.table("houses").select("id").eq("bot_jid", bot_jid).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Este bot ya está asignado a otra casa")

    # 3. Create house, assign bot_jid and add user as owner
    house = supabase.table("houses").insert({
        "bot_jid": bot_jid,
        "name":    "Mi Casa",
    }).execute().data[0]

    supabase.table("house_members").insert({
        "house_id": house["id"],
        "user_id":  current_user["id"],
        "role":     "owner",
    }).execute()

    return {"ok": True, "house_id": house["id"]}


# ── Bot identification (read-only, called on bot startup) ─────────────────────

class BotIdentifyRequest(BaseModel):
    bot_jid: str


@router.post("/bot/identify", dependencies=[Depends(verify_webhook_secret)])
def bot_identify(body: BotIdentifyRequest):
    """Bot calls this on startup to find its house_id. Read-only — never creates."""
    result = supabase.table("houses").select("id,name").eq("bot_jid", body.bot_jid.strip().lower()).execute()
    if not result.data:
        return {"house_id": None, "configured": False}
    return {"house_id": result.data[0]["id"], "configured": True}
