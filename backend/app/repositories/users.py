from app.core.db import supabase


class UserRepository:

    def find_by_id(self, user_id: str) -> dict | None:
        res = supabase.table("base_user").select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None

    def find_basic_by_id(self, user_id: str) -> dict | None:
        res = (
            supabase.table("base_user")
            .select("username, first_name, last_name")
            .eq("id", user_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_by_email(self, email: str) -> dict | None:
        res = supabase.table("base_user").select("*").eq("email", email).execute()
        return res.data[0] if res.data else None

    def find_email_by_username(self, username: str) -> str | None:
        res = (
            supabase.table("base_user")
            .select("email")
            .eq("username", username.lower())
            .execute()
        )
        return res.data[0]["email"] if res.data else None

    def exists_by_username(self, username: str) -> bool:
        res = supabase.table("base_user").select("id").eq("username", username).execute()
        return bool(res.data)

    def find_paginated(self, skip: int = 0, limit: int = 100) -> dict:
        res = (
            supabase.table("base_user")
            .select("*", count="exact")
            .range(skip, skip + limit - 1)
            .order("created_at", desc=True)
            .execute()
        )
        return {"data": res.data or [], "count": res.count or 0}

    def find_by_ids(self, user_ids: list[str], fields: str = "id, username, email") -> list[dict]:
        if not user_ids:
            return []
        return (
            supabase.table("base_user")
            .select(fields)
            .in_("id", user_ids)
            .execute()
            .data
            or []
        )

    def count_all(self) -> int:
        return supabase.table("base_user").select("id", count="exact").execute().count or 0


class XmppAccountRepository:

    def find_jid_by_user(self, user_id: str) -> str | None:
        res = (
            supabase.table("xmpp_accounts")
            .select("jid")
            .eq("user_id", user_id)
            .execute()
        )
        return res.data[0]["jid"] if res.data else None

    def find_user_id_by_jid(self, jid: str) -> str | None:
        res = (
            supabase.table("xmpp_accounts")
            .select("user_id")
            .eq("jid", jid)
            .execute()
        )
        return res.data[0]["user_id"] if res.data else None


user_repository = UserRepository()
xmpp_account_repository = XmppAccountRepository()
