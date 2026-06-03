from app.core.db import supabase


class CommandRepository:

    HISTORY_SELECT = "*, user_id, devices(name, type)"
    META_FOR_PUSH  = "user_id, source_type, action, devices(name)"

    def find_history(
        self,
        user_ids: str | list[str],
        source_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        if isinstance(user_ids, list):
            query = supabase.table("commands").select(self.HISTORY_SELECT).in_("user_id", user_ids)
        else:
            query = supabase.table("commands").select(self.HISTORY_SELECT).eq("user_id", user_ids)
        if source_type:
            query = query.eq("source_type", source_type)
        if date_from:
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)
        return (
            query
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
            .data
            or []
        )

    def find_by_id_and_user(self, command_id: str, user_id: str) -> dict | None:
        res = (
            supabase.table("commands")
            .select("*")
            .eq("id", command_id)
            .eq("user_id", user_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_meta_by_id(self, command_id: str) -> dict | None:
        res = (
            supabase.table("commands")
            .select(self.META_FOR_PUSH)
            .eq("id", command_id)
            .execute()
        )
        return res.data[0] if res.data else None


command_repository = CommandRepository()
