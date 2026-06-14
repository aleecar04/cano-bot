from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from croniter import croniter
from app.core.db import supabase
from app.core.errors import bad_request, not_found
from app.models.schedules import ScheduleCreate, GroupScheduleCreate, ScheduleMarkRun, ScheduleToggle
from app.services.home import home_service
from app.services.devices import find_devices_in_scope
from app.repositories.schedules import schedule_repository

_POWER_ACTIONS = {"encender", "apagar"}
_DB_NOW = "now()"


def _next_run(cron_expr: str, tz_name: str = "UTC") -> datetime:
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = timezone.utc
    now = datetime.now(tz)
    next_dt = croniter(cron_expr, now).get_next(datetime)
    return next_dt.replace(tzinfo=tz)


def _check_conflicting_power_schedule(device_id: str, next_run_at: datetime, action: str) -> None:
    if action not in _POWER_ACTIONS:
        return
    minute_start = next_run_at.replace(second=0, microsecond=0)
    minute_end = minute_start + timedelta(minutes=1) - timedelta(microseconds=1)
    conflicts = schedule_repository.find_conflicting_power(
        device_id=str(device_id),
        minute_start_iso=minute_start.isoformat(),
        minute_end_iso=minute_end.isoformat(),
        power_actions=list(_POWER_ACTIONS),
    )
    if conflicts:
        raise bad_request(
            "Ya existe una tarea de encendido/apagado programada para este dispositivo en ese minuto"
        )


class SchedulesService:

    def create_schedule(self, schedule_in: ScheduleCreate, user_id: str) -> dict:
        if schedule_in.cron_expr:
            next_run_at = _next_run(schedule_in.cron_expr, schedule_in.timezone)
        elif schedule_in.run_at:
            next_run_at = schedule_in.run_at
        else:
            raise bad_request("Se requiere cron_expr (recurrente) o run_at (única)")

        _check_conflicting_power_schedule(str(schedule_in.device_id), next_run_at, schedule_in.action)

        data = schedule_in.model_dump(mode="json", exclude={"run_at"})
        data.update({
            "user_id":     user_id,
            "next_run_at": next_run_at.isoformat(),
            "is_active":   True,
        })
        result = supabase.table("schedules").insert(data).execute()

        if not result.data:
            raise RuntimeError("Error al crear tarea programada")
        return result.data[0]

    def get_schedules(self, user_id: str) -> list[dict]:
        return schedule_repository.find_by_user_ids(home_service.get_house_member_ids(user_id))

    def get_schedule(self, schedule_id: str, user_id: str) -> dict | None:
        return schedule_repository.find_by_id_and_user(schedule_id, user_id)

    def delete_schedule(self, schedule_id: str, user_id: str) -> bool:
        result = (
            supabase.table("schedules")
            .delete()
            .eq("id", schedule_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(result.data)

    def delete_schedule_any(self, schedule_id: str, user_id: str) -> bool:
        member_ids = home_service.get_house_member_ids(user_id)
        result = (
            supabase.table("schedules")
            .delete()
            .eq("id", schedule_id)
            .in_("user_id", member_ids)
            .execute()
        )
        return bool(result.data)

    def toggle_schedule(
        self, schedule_id: str, user_id: str, toggle_in: ScheduleToggle
    ) -> dict | None:
        update: dict = {
            "is_active": toggle_in.is_active,
            "updated_at": _DB_NOW,
        }
        if toggle_in.is_active:
            existing = self.get_schedule(schedule_id, user_id)
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
        self, schedule_id: str, owner_id: str, toggle_in: ScheduleToggle
    ) -> dict | None:
        """Owner-only: toggle any schedule in the house."""
        member_ids = home_service.get_house_member_ids(owner_id)
        s = schedule_repository.find_cron_meta_in_house(schedule_id, member_ids)
        if not s:
            return None
        update: dict = {"is_active": toggle_in.is_active, "updated_at": _DB_NOW}
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

    def delete_completed_schedules(self, user_id: str) -> int:
        query = (
            supabase.table("schedules")
            .delete()
            .is_("cron_expr", "null")
            .eq("is_active", False)
        )
        if home_service.get_user_role(user_id) == "owner":
            member_ids = home_service.get_house_member_ids(user_id)
            query = query.in_("user_id", member_ids)
        else:
            query = query.eq("user_id", user_id)
        result = query.execute()
        return len(result.data) if result.data else 0

    def get_pending_schedules(self) -> list[dict]:
        return schedule_repository.find_pending(datetime.now(timezone.utc).isoformat())

    def create_group_schedule(
        self,
        scope: str,
        scope_id: str,
        schedule_in: GroupScheduleCreate,
        user_id: str,
    ) -> dict:
        devices = find_devices_in_scope(scope, scope_id, fields="id,name")
        created = 0
        for d in devices:
            try:
                data = schedule_in.model_dump()
                data["name"] = f"{schedule_in.name}: {d.get('name', d['id'])}"
                s = ScheduleCreate(**data, device_id=d["id"])
                self.create_schedule(s, user_id)
                created += 1
            except ValueError:
                pass  # skip conflicting schedules silently
        return {"ok": True, "created": created}

    def mark_schedule_run(self, schedule_id: str, run_in: ScheduleMarkRun) -> None:
        s = schedule_repository.find_cron_meta_by_id(schedule_id)
        if not s:
            return

        update: dict = {
            "last_command_id": run_in.command_id,
            "updated_at":      _DB_NOW,
        }

        if s["cron_expr"]:
            tz = s.get("timezone") or "UTC"
            update["next_run_at"] = _next_run(s["cron_expr"], tz).isoformat()
        else:
            update["is_active"] = False

        supabase.table("schedules").update(update).eq("id", schedule_id).execute()


schedules_service = SchedulesService()
