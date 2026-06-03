from app.core.db import supabase


class ScheduleRepository:

    LIST_SELECT = (
        "*, devices(name, type), "
        "last_command:commands!last_command_id(status, error, executed_at)"
    )

    def find_conflicting_power(
        self,
        device_id: str,
        minute_start_iso: str,
        minute_end_iso: str,
        power_actions: list[str],
    ) -> list[dict]:
        return (
            supabase.table("schedules")
            .select("id")
            .eq("device_id", device_id)
            .eq("is_active", True)
            .in_("action", power_actions)
            .gte("next_run_at", minute_start_iso)
            .lte("next_run_at", minute_end_iso)
            .execute()
            .data
            or []
        )

    def find_by_user_ids(self, user_ids: list[str]) -> list[dict]:
        return (
            supabase.table("schedules")
            .select(self.LIST_SELECT)
            .in_("user_id", user_ids)
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )

    def find_by_id_and_user(self, schedule_id: str, user_id: str) -> dict | None:
        res = (
            supabase.table("schedules")
            .select("*")
            .eq("id", schedule_id)
            .eq("user_id", user_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_cron_meta_in_house(self, schedule_id: str, user_ids: list[str]) -> dict | None:
        res = (
            supabase.table("schedules")
            .select("cron_expr, timezone, user_id")
            .eq("id", schedule_id)
            .in_("user_id", user_ids)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_cron_meta_by_id(self, schedule_id: str) -> dict | None:
        res = (
            supabase.table("schedules")
            .select("cron_expr, timezone")
            .eq("id", schedule_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_pending(self, now_iso: str) -> list[dict]:
        return (
            supabase.table("schedules")
            .select("*")
            .lte("next_run_at", now_iso)
            .eq("is_active", True)
            .execute()
            .data
            or []
        )

schedule_repository = ScheduleRepository()
