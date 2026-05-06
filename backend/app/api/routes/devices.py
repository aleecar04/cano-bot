from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from app.api.deps import CurrentUser
from app.api.routes.messages import verify_webhook_secret
from app.models import DeviceVincular, DevicePublic, DeviceUpdate, DeviceStatusUpdate, CommandCreate
from app.services import devices as device_service
from app.services.home import require_house, get_user_role, get_house_member_ids
from app.services.devices import HAConnectSchema
from app.core.db import supabase

router = APIRouter(prefix="/devices", tags=["devices"])

_NOT_FOUND = "Dispositivo no encontrado"


@router.post(
    "/vincular",
    response_model=DevicePublic,
    responses={
        400: {"description": "Invalid device data"},
        401: {"description": "Not authenticated"},
        500: {"description": "Internal error while linking device"},
    },
)
async def vincular_device(device_in: DeviceVincular, current_user: CurrentUser):
    try:
        device = device_service.vincular_device(device_in, current_user["id"])
        await device_service.request_device_poll(device["id"], current_user["id"])
        return device
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        msg = str(e)
        if "house_id_name" in msg or "unique" in msg.lower():
            raise HTTPException(status_code=409, detail="Ya existe un dispositivo con ese nombre en esta casa")
        raise HTTPException(status_code=500, detail=msg)


@router.get(
    "/",
    response_model=list[DevicePublic],
    responses={
        401: {"description": "Not authenticated"},
    },
)
def get_devices(current_user: CurrentUser):
    return device_service.get_devices(current_user["id"])


@router.get(
    "/all",
    response_model=list[DevicePublic],
    dependencies=[Depends(verify_webhook_secret)],
    responses={401: {"description": "Invalid webhook token"}},
)
def get_all_devices(user_id: Annotated[Optional[str], Query()] = None):
    """Bot-only endpoint: returns all house devices for a given user."""
    return device_service.get_all_devices(user_id=user_id)


@router.get("/commands")
def get_my_commands(
    current_user: CurrentUser,
    limit: int = Query(default=50, le=200),
    page: int = Query(default=1, ge=1),
    source_type: Annotated[Optional[str], Query()] = None,
    date_from: Annotated[Optional[str], Query()] = None,
    date_to: Annotated[Optional[str], Query()] = None,
    member_id: Annotated[Optional[str], Query()] = None,
):
    """Returns paginated command history.
    Owners can pass member_id=<uuid> to filter by a specific house member,
    or member_id=all to see the entire house history."""
    user_id = current_user["id"]
    offset  = (page - 1) * limit

    # Resolve which user IDs to query
    if member_id and get_user_role(user_id) == "owner":
        if member_id == "all":
            target_ids = get_house_member_ids(user_id)
            query = supabase.table("commands").select("*, user_id, devices(name, type)").in_("user_id", target_ids)
        else:
            house_ids = get_house_member_ids(user_id)
            safe_id = member_id if member_id in house_ids else user_id
            query = supabase.table("commands").select("*, user_id, devices(name, type)").eq("user_id", safe_id)
    else:
        query = supabase.table("commands").select("*, user_id, devices(name, type)").eq("user_id", user_id)

    if source_type:
        query = query.eq("source_type", source_type)
    if date_from:
        query = query.gte("created_at", date_from)
    if date_to:
        query = query.lte("created_at", date_to)
    result = (
        query
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data or []


@router.get("/commands/{command_id}")
def get_command(command_id: str, current_user: CurrentUser):
    result = (
        supabase.table("commands")
        .select("*")
        .eq("id", command_id)
        .eq("user_id", current_user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Comando no encontrado")
    return result.data[0]


@router.get(
    "/{device_id}",
    response_model=DevicePublic,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": _NOT_FOUND},
    },
)
def get_device(device_id: str, current_user: CurrentUser):
    device = device_service.get_device(device_id, current_user["id"])
    if not device:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return device


@router.patch(
    "/{device_id}",
    response_model=DevicePublic,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": _NOT_FOUND},
    },
)
def update_device(device_id: str, device_in: DeviceUpdate, current_user: CurrentUser):
    data = device_in.model_dump(exclude_none=True)
    if "room_id" in data:
        data["room_id"] = str(data["room_id"]) if data["room_id"] else None
    updated = device_service.update_device(device_id, current_user["id"], data)
    if not updated:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return updated


@router.delete(
    "/{device_id}",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": _NOT_FOUND},
    },
)
def desvincular_device(device_id: str, current_user: CurrentUser):
    ok = device_service.desvincular_device(device_id, current_user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return {"ok": True}


@router.patch(
    "/{device_id}/status",
    responses={
        401: {"description": "Invalid webhook token"},
        404: {"description": _NOT_FOUND},
    },
)
def update_status(
    device_id: str,
    status_in: DeviceStatusUpdate,
    _: Annotated[None, Depends(verify_webhook_secret)],
):
    ok = device_service.update_device_status(device_id, status_in)
    if not ok:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return {"ok": True}


@router.post(
    "/{device_id}/command",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": _NOT_FOUND},
        500: {"description": "Internal error while sending command"},
    },
)
async def send_command(device_id: str, command_in: CommandCreate, current_user: CurrentUser):
    try:
        require_house(current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    try:
        return await device_service.send_command(device_id, command_in, current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.patch(
    "/{device_id}/config",
    responses={
        401: {"description": "Invalid webhook token"},
        404: {"description": _NOT_FOUND},
    },
)
def update_config(
    device_id: str,
    config: dict,
    _: Annotated[None, Depends(verify_webhook_secret)],
):
    device_service.update_device_config(device_id, config)
    return {"ok": True}


@router.get(
    "/{device_id}/status",
    dependencies=[Depends(verify_webhook_secret)],
)
def get_device_status(device_id: str):
    result = supabase.table("devices")\
        .select("id, is_online, estado, updated_at")\
        .eq("id", device_id)\
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    d = result.data[0]
    return {
        "device_id":  d["id"],
        "is_online":  d["is_online"],
        "estado":     d["estado"] or {},
        "last_update": d["updated_at"],
    }

@router.post("/ha/connect")
def ha_connect(data: HAConnectSchema, current_user: CurrentUser):
    try:
        return device_service.connect_ha(current_user["id"], data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ha/connection")
def get_ha_connection(current_user: CurrentUser):
    result = supabase.table("ha_integrations").select("ha_url,created_at").eq("user_id", current_user["id"]).execute()
    if not result.data:
        return {"connected": False}
    return {"connected": True, "ha_url": result.data[0]["ha_url"], "created_at": result.data[0]["created_at"]}


@router.post("/ha/reimport")
def ha_reimport(current_user: CurrentUser):
    """Re-imports HA devices using the already stored credentials."""
    row = supabase.table("ha_integrations").select("ha_url, token").eq("user_id", current_user["id"]).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="No hay integración de Home Assistant configurada")
    stored = row.data[0]
    try:
        result = device_service.connect_ha(current_user["id"], device_service.HAConnectSchema(
            ha_url=stored["ha_url"], token=stored["token"]
        ))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/ha/connection")
def delete_ha_connection(current_user: CurrentUser):
    supabase.table("ha_integrations").delete().eq("user_id", current_user["id"]).execute()
    supabase.table("devices").delete().eq("owner_id", current_user["id"]).eq("driver", "homeassistant").execute()
    return {"ok": True}