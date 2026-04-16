from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from app.api.deps import CurrentUser
from app.api.routes.messages import verify_webhook_secret
from app.models import DeviceVincular, DevicePublic, DeviceStatusUpdate, CommandCreate
from app.services import devices as device_service
from app.services.devices import HAConnectSchema
from app.core.db import supabase

router = APIRouter(prefix="/devices", tags=["devices"])


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
        return device_service.vincular_device(device_in, current_user["id"])  # ← sin await
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    "/{device_id}",
    response_model=DevicePublic,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Dispositivo no encontrado"},
    },
)
def get_device(device_id: str, current_user: CurrentUser):
    device = device_service.get_device(device_id, current_user["id"])
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return device


@router.delete(
    "/{device_id}",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Dispositivo no encontrado"},
    },
)
def desvincular_device(device_id: str, current_user: CurrentUser):
    ok = device_service.desvincular_device(device_id, current_user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return {"ok": True}


@router.patch(
    "/{device_id}/status",
    responses={
        401: {"description": "Invalid webhook token"},
        404: {"description": "Dispositivo no encontrado"},
    },
)
def update_status(
    device_id: str,
    status_in: DeviceStatusUpdate,
    _: Annotated[None, Depends(verify_webhook_secret)],
):
    ok = device_service.update_device_status(device_id, status_in)
    if not ok:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return {"ok": True}


@router.post(
    "/{device_id}/command",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Dispositivo no encontrado"},
        500: {"description": "Internal error while sending command"},
    },
)
async def send_command(device_id: str, command_in: CommandCreate, current_user: CurrentUser):
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
        404: {"description": "Dispositivo no encontrado"},
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
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    d = result.data[0]
    return {
        "device_id":  d["id"],
        "is_online":  d["is_online"],
        "estado":     d["estado"] or {},
        "last_update": d["updated_at"],
    }

@router.get(
    "/all",
    response_model=list[DevicePublic],
    dependencies=[Depends(verify_webhook_secret)],
    responses={401: {"description": "Invalid webhook token"}},
)
def get_all_devices(owner_id: Optional[str] = Query(default=None)):
    """Bot-only endpoint: returns devices for polling. Optionally filter by owner."""
    return device_service.get_all_devices(owner_id=owner_id)


@router.post("/ha/connect")
def ha_connect(data: HAConnectSchema, current_user: CurrentUser):
    try:
        return device_service.connect_ha(current_user["id"], data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))