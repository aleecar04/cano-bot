"""
Central command execution service.
All command origins (direct, conversation, favorite, schedule) go through
execute_command(), which ensures every execution is recorded in the commands
table before the action is dispatched to the bot.
"""
from __future__ import annotations

import json
from app.core.db import supabase
from app.core.config import settings
from app.services.xmpp import send_xmpp_message
from app.services.home import get_bot_jid_for_user


# ── Strategy pattern ─────────────────────────────────────────────────────────

class CommandSource:
    """Base strategy — direct app control, conversation, favorite.
    These share identical post-execute behaviour (nothing extra to do)."""

    def __init__(self, source_type: str = "direct", source_id: str | None = None):
        self.source_type = source_type
        self.source_id = source_id

    def post_execute(self, schedule_id: str | None, command_id: str) -> None:
        pass


class ScheduleSource(CommandSource):
    """Strategy for scheduled task execution.
    post_execute updates last_command_id and recalculates next_run_at."""

    def __init__(self, schedule_id: str):
        super().__init__(source_type="schedule", source_id=schedule_id)

    def post_execute(self, schedule_id: str | None, command_id: str) -> None:
        from app.services.schedules import mark_schedule_run
        from app.models import ScheduleMarkRun
        mark_schedule_run(self.source_id, ScheduleMarkRun(command_id=command_id))


# ── Core executor ─────────────────────────────────────────────────────────────

def _create_pending_command(
    user_id: str,
    device_id: str,
    action: str,
    payload: dict,
    source_type: str,
    source_id: str | None,
) -> str:
    result = supabase.table("commands").insert({
        "user_id":     user_id,
        "device_id":   device_id,
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


async def execute_command(
    device_id: str,
    action: str,
    payload: dict,
    user_id: str,
    source: CommandSource,
) -> dict:
    """
    1. Create pending command record.
    2. Dispatch to bot via XMPP.
    3. post_execute hook (only ScheduleSource does anything here).
    Returns {"ok": True, "command_id": ...}.
    """
    device = supabase.table("devices").select("*").eq("id", device_id).execute()
    if not device.data:
        raise ValueError("Dispositivo no encontrado")

    # Get user XMPP credentials
    jid_result = supabase.table("xmpp_accounts").select("jid").eq("user_id", user_id).execute()
    if not jid_result.data:
        raise ValueError("Cuenta XMPP no encontrada")
    jid = jid_result.data[0]["jid"]

    password_result = supabase.rpc("get_xmpp_password", {
        "p_user_id": user_id,
        "p_key": settings.XMPP_ENCRYPTION_KEY
    }).execute()
    xmpp_password = password_result.data

    bot_jid = get_bot_jid_for_user(user_id)
    if not bot_jid:
        raise ValueError("La casa no tiene un bot configurado")

    command_id = _create_pending_command(
        user_id=user_id,
        device_id=device_id,
        action=action,
        payload=payload,
        source_type=source.source_type,
        source_id=source.source_id,
    )

    try:
        await send_xmpp_message(
            body=json.dumps({
                "device_id":  device_id,
                "accion":     action,
                "payload":    payload,
                "command_id": command_id,
            }),
            from_jid=jid,
            xmpp_password=xmpp_password,
            to_jid=bot_jid,
        )
    except Exception as e:
        _update_command(command_id, error=f"XMPP error: {e}")
        raise

    source.post_execute(source.source_id, command_id)
    return {"ok": True, "command_id": command_id}
