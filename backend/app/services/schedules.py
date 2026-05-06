from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from croniter import croniter
from app.core.db import supabase
from app.models import ScheduleCreate, ScheduleMarkRun, ScheduleToggle
from app.services.home import get_house_member_ids

_POWER_ACTIONS = {"encender", "apagar"}


def _next_run(cron_expr: str, tz_name: str = "UTC") -> datetime:
    """Return the next fire time for a cron expression in the given timezone."""
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = timezone.utc
    now = datetime.now(tz)
    next_dt = croniter(cron_expr, now).get_next(datetime)
    return next_dt.replace(tzinfo=tz)


def _check_conflicting_power_schedule(device_id: str, next_run_at: datetime, action: str) -> None:
    """Reject if there's already a power action scheduled for the same device in the same minute."""
    if action not in _POWER_ACTIONS:
        return
    minute_start = next_run_at.replace(second=0, microsecond=0)
    minute_end = minute_start + timedelta(minutes=1) - timedelta(microseconds=1)
    result = (
        supabase.table("schedules")
        .select("id")
        .eq("device_id", str(device_id))
        .eq("is_active", True)
        .in_("action", list(_POWER_ACTIONS))
        .gte("next_run_at", minute_start.isoformat())
        .lte("next_run_at", minute_end.isoformat())
        .execute()
    )
    if result.data:
        raise ValueError(
            "Ya existe una tarea de encendido/apagado programada para este dispositivo en ese minuto"
        )


def create_schedule(schedule_in: ScheduleCreate, user_id: str) -> dict:
    if schedule_in.cron_expr:
        next_run_at = _next_run(schedule_in.cron_expr, schedule_in.timezone)
    elif schedule_in.run_at:
        next_run_at = schedule_in.run_at
    else:
        raise ValueError("Se requiere cron_expr (recurrente) o run_at (única)")

    _check_conflicting_power_schedule(str(schedule_in.device_id), next_run_at, schedule_in.action)

    result = (
        supabase.table("schedules")
        .insert({
            "user_id":     user_id,
            "device_id":   str(schedule_in.device_id),
            "name":        schedule_in.name,
            "action":      schedule_in.action,
            "payload":     schedule_in.payload,
            "cron_expr":   schedule_in.cron_expr,
            "next_run_at": next_run_at.isoformat(),
            "is_active":   True,
            "timezone":    schedule_in.timezone,
        })
        .execute()
    )

    if not result.data:
        raise RuntimeError("Error al crear tarea programada")
    return result.data[0]


def get_schedules(user_id: str) -> list[dict]:
    """Return all schedules for every member of the user's house,
    including last command status via a JOIN on last_command_id."""
    member_ids = get_house_member_ids(user_id)
    result = (
        supabase.table("schedules")
        .select("*, devices(name, type), last_command:commands!last_command_id(status, error, executed_at)")
        .in_("user_id", member_ids)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def get_schedule(schedule_id: str, user_id: str) -> dict | None:
    result = (
        supabase.table("schedules")
        .select("*")
        .eq("id", schedule_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def delete_schedule(schedule_id: str, user_id: str) -> bool:
    """Delete own schedule."""
    result = (
        supabase.table("schedules")
        .delete()
        .eq("id", schedule_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(result.data)


def delete_schedule_any(schedule_id: str, user_id: str) -> bool:
    """Owner-only: delete any schedule in the house."""
    from app.services.home import get_house_member_ids
    member_ids = get_house_member_ids(user_id)
    result = (
        supabase.table("schedules")
        .delete()
        .eq("id", schedule_id)
        .in_("user_id", member_ids)
        .execute()
    )
    return bool(result.data)


def toggle_schedule(
    schedule_id: str, user_id: str, toggle_in: ScheduleToggle
) -> dict | None:
    update: dict = {
        "is_active": toggle_in.is_active,
        "updated_at": "now()",
    }
    if toggle_in.is_active:
        existing = get_schedule(schedule_id, user_id)
        if existing and existing.get("cron_expr"):
            tz = existing.get("timezone") or "UTC"
            update["next_run_at"] = _next_run(existing["cron_expr"], tz).isoformat()

    result = (
        supabase.table("schedules")
        .update(update)
        .eq("id", schedule_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def toggle_schedule_any(
    schedule_id: str, owner_id: str, toggle_in: ScheduleToggle
) -> dict | None:
    """Owner-only: toggle any schedule in the house."""
    member_ids = get_house_member_ids(owner_id)
    existing = (
        supabase.table("schedules")
        .select("cron_expr, timezone, user_id")
        .eq("id", schedule_id)
        .in_("user_id", member_ids)
        .execute()
    )
    if not existing.data:
        return None
    s = existing.data[0]
    update: dict = {"is_active": toggle_in.is_active, "updated_at": "now()"}
    if toggle_in.is_active and s.get("cron_expr"):
        tz = s.get("timezone") or "UTC"
        update["next_run_at"] = _next_run(s["cron_expr"], tz).isoformat()
    result = (
        supabase.table("schedules")
        .update(update)
        .eq("id", schedule_id)
        .execute()
    )
    return result.data[0] if result.data else None


def delete_completed_schedules(user_id: str) -> int:
    """Delete one-time completed schedules.
    Owners delete for the whole house; members delete only their own."""
    from app.services.home import get_user_role
    query = (
        supabase.table("schedules")
        .delete()
        .is_("cron_expr", "null")
        .eq("is_active", False)
    )
    if get_user_role(user_id) == "owner":
        member_ids = get_house_member_ids(user_id)
        query = query.in_("user_id", member_ids)
    else:
        query = query.eq("user_id", user_id)
    result = query.execute()
    return len(result.data) if result.data else 0


def get_pending_schedules() -> list[dict]:
    """Return all active schedules whose next_run_at is in the past. Called by the bot."""
    now = datetime.now(timezone.utc)
    result = (
        supabase.table("schedules")
        .select("*")
        .lte("next_run_at", now.isoformat())
        .eq("is_active", True)
        .execute()
    )
    return result.data or []


def mark_schedule_run(schedule_id: str, run_in: ScheduleMarkRun) -> None:
    """Update a schedule after the bot executes it. Called via webhook."""
    existing = (
        supabase.table("schedules")
        .select("cron_expr, timezone")
        .eq("id", schedule_id)
        .execute()
    )

    if not existing.data:
        return

    s = existing.data[0]
    update: dict = {
        "last_command_id": run_in.command_id,
        "updated_at":      "now()",
    }

    if s["cron_expr"]:
        tz = s.get("timezone") or "UTC"
        update["next_run_at"] = _next_run(s["cron_expr"], tz).isoformat()
    else:
        update["is_active"] = False

    supabase.table("schedules").update(update).eq("id", schedule_id).execute()
