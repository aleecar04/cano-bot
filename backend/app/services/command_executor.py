from __future__ import annotations

import json
from app.core.db import supabase
from app.core.config import settings
from app.core.errors import bad_request, conflict, not_found
from app.services.xmpp import send_xmpp_message
from app.services.home import get_bot_target_for_user, get_house_id_for_user
from app.services.device_catalog import is_action_supported, validate_payload
from app.repositories.devices import device_repository
from app.repositories.users import xmpp_account_repository


# ── Strategy pattern ─────────────────────────────────────────────────────────

class CommandSource:

    def __init__(self, source_type: str = "direct", source_id: str | None = None):
        self.source_type = source_type
        self.source_id = source_id

    def post_execute(self, schedule_id: str | None, command_id: str) -> None:
        pass


class ScheduleSource(CommandSource):
    
    def __init__(self, schedule_id: str):
        super().__init__(source_type="schedule", source_id=schedule_id)

    def post_execute(self, schedule_id: str | None, command_id: str) -> None:
        from app.services.schedules import mark_schedule_run
        from app.models.schedules import ScheduleMarkRun
        mark_schedule_run(self.source_id, ScheduleMarkRun(command_id=command_id))


# ── Core executor ─────────────────────────────────────────────────────────────

def _create_pending_command(
    user_id: str,
    device_id: str | None,
    target_type: str,
    action: str,
    payload: dict,
    source_type: str,
    source_id: str | None,
) -> str:
    result = supabase.table("commands").insert({
        "user_id":     user_id,
        "device_id":   device_id,
        "target_type": target_type,
        "action":      action,
        "payload":     payload,
        "status":      "pending",
        "source_type": source_type,
        "source_id":   source_id,
    }).execute()
    return result.data[0]["id"]


def _update_command(command_id: str, error: str | None) -> None:
    status = "failed" if error else "executed"
    data: dict = {"status": status, "executed_at": "now()"}
    if error:
        data["error"] = error
    supabase.table("commands").update(data).eq("id", command_id).execute()


def _get_xmpp_context(user_id: str) -> tuple[str, str, str]:
    jid = xmpp_account_repository.find_jid_by_user(user_id)
    if not jid:
        raise not_found("Cuenta XMPP no encontrada")
    password_result = supabase.rpc("get_xmpp_password", {
        "p_user_id": user_id,
        "p_key": settings.XMPP_ENCRYPTION_KEY,
    }).execute()
    bot_target = get_bot_target_for_user(user_id)
    if not bot_target:
        raise bad_request("La casa no tiene un bot configurado")
    return jid, password_result.data, bot_target


def _resolve_target(user_id: str, device_id: str | None) -> tuple[str, dict | None]:
    if not device_id:
        return "system", None
    house_id = get_house_id_for_user(user_id)
    device = device_repository.find_by_id_and_house(device_id, house_id)
    if not device:
        raise not_found("Dispositivo no encontrado")
    return "device", device


def _build_command_body(device_id: str | None, action: str, payload: dict, command_id: str) -> str:
    if device_id:
        return json.dumps({
            "device_id":  device_id,
            "action":     action,
            "payload":    payload,
            "command_id": command_id,
        })
    return json.dumps({"type": action, "command_id": command_id})  # system, p.ej. "scan"


async def execute_command(
    action: str,
    payload: dict,
    user_id: str,
    source: CommandSource,
    device_id: str | None = None,
    target_type: str | None = None,
) -> dict:
    jid, xmpp_password, bot_target = _get_xmpp_context(user_id)
    device = None
    if target_type is None:
        target_type, device = _resolve_target(user_id, device_id)

    if target_type == "device":
        if device is None:
            _, device = _resolve_target(user_id, device_id)
        if device and not is_action_supported(device.get("type", ""), action):
            raise conflict(f"{device['name']} no soporta la acción '{action}'.")
        err = validate_payload(action, payload)
        if err:
            raise conflict(err)

    command_id = _create_pending_command(
        user_id=user_id,
        device_id=device_id,
        target_type=target_type,
        action=action,
        payload=payload,
        source_type=source.source_type,
        source_id=source.source_id,
    )

    body = _build_command_body(device_id, action, payload, command_id)
    try:
        await send_xmpp_message(body=body, from_jid=jid, xmpp_password=xmpp_password, to_jid=bot_target)
    except Exception as e:
        _update_command(command_id, error=f"XMPP error: {e}")
        raise

    source.post_execute(source.source_id, command_id)
    return {"ok": True, "command_id": command_id}
