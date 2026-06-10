from app.core.db import supabase


class FavoriteRepository:

    def find_by_user(self, user_id: str) -> list[dict]:
        return (
            supabase.table("favorite_actions")
            .select("*, devices(name, type)")
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
            .data
            or []
        )

    def find_by_id_and_user(self, favorite_id: str, user_id: str) -> dict | None:
        res = (
            supabase.table("favorite_actions")
            .select("*")
            .eq("id", favorite_id)
            .eq("user_id", user_id)
            .execute()
        )
        return res.data[0] if res.data else None


favorite_repository = FavoriteRepository()
