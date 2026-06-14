from fastapi import APIRouter
from app.api.deps import CurrentUser
from app.core.errors import conflict, not_found
from app.models.houses import (
    HousePublic, FloorPublic, RoomPublic, FloorCreate, RoomCreate,
    GroupActionRequest, InviteCodeResponse, JoinRequest,
    HouseSetupRequest,
)
from app.models.schedules import GroupScheduleCreate
from app.services.home import home_service
from app.services.devices import devices_service as device_service
from app.services.schedules import schedules_service
from app.services.xmpp import xmpp_service

router = APIRouter(prefix="/houses", tags=["houses"])

_HOUSE_NOT_FOUND = "Casa no encontrada"


@router.get("/me", response_model=HousePublic)
def get_my_house(current_user: CurrentUser):
    house = home_service.get_house_with_detail(current_user["id"])
    if not house:
        raise not_found(_HOUSE_NOT_FOUND)
    return house


@router.get("/me/bot-status")
async def get_bot_status(current_user: CurrentUser):
    bot_jid = home_service.get_bot_target_for_user(current_user["id"])
    if not bot_jid:
        return {"online": False}
    return {"online": await xmpp_service.is_bot_online(bot_jid)}


@router.get("/me/rooms", response_model=list[RoomPublic])
def get_my_rooms(current_user: CurrentUser):
    """Flat list of all rooms — used for device-assignment selects."""
    house = home_service.get_user_house(current_user["id"])
    if not house:
        raise not_found(_HOUSE_NOT_FOUND)
    return home_service.get_rooms_by_house(house["id"])


@router.post("/me/floors", response_model=FloorPublic, status_code=201)
def add_floor(floor_in: FloorCreate, current_user: CurrentUser):
    house = home_service.get_user_house(current_user["id"])
    if not house:
        raise not_found(_HOUSE_NOT_FOUND)
    home_service.require_owner(current_user["id"])
    try:
        floor = home_service.create_floor(house["id"], floor_in.name)
    except Exception:
        raise conflict("Ya existe una planta con ese nombre")
    floor["rooms"] = []
    return floor


@router.post("/floors/{floor_id}/rooms", response_model=RoomPublic, status_code=201)
def add_room(floor_id: str, room_in: RoomCreate, current_user: CurrentUser):
    home_service.require_owner(current_user["id"])
    try:
        room = home_service.create_room(floor_id, room_in.name)
    except Exception:
        raise conflict("Ya existe una habitación con ese nombre en esta planta")
    return room


@router.delete("/floors/{floor_id}/rooms/{room_id}", status_code=204)
def delete_room(floor_id: str, room_id: str, current_user: CurrentUser):
    home_service.delete_room(current_user["id"], floor_id, room_id)


@router.delete("/floors/{floor_id}", status_code=204)
def delete_floor(floor_id: str, current_user: CurrentUser):
    home_service.delete_floor(current_user["id"], floor_id)


# ── Group actions ────────────────────────────────────────────────────────────

@router.post("/rooms/{room_id}/action")
async def room_action(room_id: str, body: GroupActionRequest, current_user: CurrentUser):
    return await device_service.send_group_command("room", room_id, body.action, current_user["id"])


@router.post("/floors/{floor_id}/action")
async def floor_action(floor_id: str, body: GroupActionRequest, current_user: CurrentUser):
    return await device_service.send_group_command("floor", floor_id, body.action, current_user["id"])


# ── Group schedules ──────────────────────────────────────────────────────────

@router.post("/rooms/{room_id}/schedule")
def room_schedule(room_id: str, schedule_in: GroupScheduleCreate, current_user: CurrentUser):
    return schedules_service.create_group_schedule("room", room_id, schedule_in, current_user["id"])


@router.post("/floors/{floor_id}/schedule")
def floor_schedule(floor_id: str, schedule_in: GroupScheduleCreate, current_user: CurrentUser):
    return schedules_service.create_group_schedule("floor", floor_id, schedule_in, current_user["id"])


# ── House members ─────────────────────────────────────────────────────────────

@router.get("/me/members", responses={404: {"description": "Casa no encontrada"}})
def get_members(current_user: CurrentUser):
    return home_service.list_house_members(current_user["id"])


# ── Invitation codes ──────────────────────────────────────────────────────────

@router.post("/me/invite", response_model=InviteCodeResponse)
def generate_invite(current_user: CurrentUser):
    house = home_service.get_user_house(current_user["id"])
    if not house:
        raise not_found("No tienes una casa asignada")
    code = home_service.generate_invitation_code(house["id"], current_user["id"])
    return {"code": code, "expires_in_hours": 24}


@router.post("/join", status_code=200)
def join_house(body: JoinRequest, current_user: CurrentUser):
    house = home_service.consume_invitation_code(body.code, current_user["id"])
    return {"ok": True, "house_id": house["id"]}


# ── Member management ────────────────────────────────────────────────────────

@router.delete("/me/members/{user_id}", status_code=204)
def kick_member(user_id: str, current_user: CurrentUser):
    home_service.kick_member(current_user["id"], user_id)


@router.delete("/me/leave", status_code=204)
def leave_house(current_user: CurrentUser):
    home_service.leave_house(current_user["id"])


# ── House setup ──────────────────────────────────────────────────────────────

@router.post("/setup", status_code=201)
def setup_house(body: HouseSetupRequest, current_user: CurrentUser):
    return home_service.setup_house(current_user["id"], body.name)


@router.post("/me/bot-token/regenerate")
def regenerate_bot_token(current_user: CurrentUser):
    return {"bot_token": home_service.regenerate_bot_token(current_user["id"])}
