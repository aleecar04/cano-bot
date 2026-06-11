from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from app.api.deps import CurrentUser
from app.api.bot_auth import bot_auth
from app.core.errors import not_found
from app.models.devices import DeviceVincular, DevicePublic, DeviceUpdate, DeviceStatusUpdate, HAConnectSchema
from app.services import devices as device_service
from app.services import commands as command_service

router = APIRouter(prefix="/devices", tags=["devices"])

_NOT_FOUND = "Dispositivo no encontrado"


@router.post(
    "/vincular",
    response_model=DevicePublic,
    responses={
        400: {"description": "Invalid device data"},
        401: {"description": "Not authenticated"},
        409: {"description": "Device name already exists in this house"},
        500: {"description": "Internal error while linking device"},
    },
)
async def vincular_device(device_in: DeviceVincular, current_user: CurrentUser):
    device = device_service.vincular_device(device_in, current_user["id"])
    await device_service.request_device_poll(device["id"], current_user["id"])
    return device


@router.get(
    "/",
    response_model=list[DevicePublic],
    responses={401: {"description": "Not authenticated"}},
)
def get_devices(current_user: CurrentUser):
    return device_service.get_devices(current_user["id"])


@router.get(
    "/all",
    response_model=list[DevicePublic],
    responses={401: {"description": "Invalid bot token"}},
)
def get_all_devices(house: dict = Depends(bot_auth)):
    """Bot-only endpoint: devuelve los devices de la casa autenticada por bot_token."""
    return device_service.get_devices_for_house(house["id"])


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
    return command_service.get_command_history(
        user_id=current_user["id"],
        page=page,
        limit=limit,
        source_type=source_type,
        date_from=date_from,
        date_to=date_to,
        member_id=member_id,
    )


@router.get("/commands/{command_id}")
def get_command(command_id: str, current_user: CurrentUser):
    return command_service.get_command_by_id(command_id, current_user["id"])


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
        raise not_found(_NOT_FOUND)
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
        raise not_found(_NOT_FOUND)
    return updated


@router.post("/{device_id}/refresh", status_code=202)
async def refresh_device(device_id: str, current_user: CurrentUser):
    if not device_service.get_device(device_id, current_user["id"]):
        raise not_found(_NOT_FOUND)
    await device_service.request_device_poll(device_id, current_user["id"])
    return {"ok": True}


@router.delete(
    "/{device_id}",
    responses={401: {"description": "Not authenticated"}},
)
def desvincular_device(device_id: str, current_user: CurrentUser):
    device_service.desvincular_device(device_id, current_user["id"])
    return {"ok": True}


@router.patch(
    "/{device_id}/status",
    responses={401: {"description": "Invalid bot token"}},
)
def update_status(device_id: str, status_in: DeviceStatusUpdate, house: dict = Depends(bot_auth)):
    device_service.update_device_status_in_house(device_id, house["id"], status_in)
    return {"ok": True}


@router.patch(
    "/{device_id}/config",
    responses={401: {"description": "Invalid bot token"}},
)
def update_config(device_id: str, config: dict, house: dict = Depends(bot_auth)):
    device_service.update_device_config_in_house(device_id, house["id"], config)
    return {"ok": True}


@router.get("/{device_id}/status")
def get_device_status(device_id: str, house: dict = Depends(bot_auth)):
    return device_service.get_status_for_bot_in_house(device_id, house["id"])


# ── Home Assistant integration ──────────────────────────────────────────────

@router.post("/ha/connect")
def ha_connect(data: HAConnectSchema, current_user: CurrentUser):
    return device_service.connect_ha(current_user["id"], data)


@router.get("/ha/connection")
def get_ha_connection(current_user: CurrentUser):
    return device_service.get_ha_connection(current_user["id"])


@router.post("/ha/reimport")
def ha_reimport(current_user: CurrentUser):
    """Re-imports HA devices using the already stored credentials."""
    return device_service.reimport_ha(current_user["id"])


@router.delete("/ha/connection")
def delete_ha_connection(current_user: CurrentUser):
    device_service.disconnect_ha(current_user["id"])
    return {"ok": True}
