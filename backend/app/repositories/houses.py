from app.core.db import supabase


class HouseRepository:

    def find_by_id(self, house_id: str) -> dict | None:
        res = supabase.table("houses").select("*").eq("id", house_id).execute()
        return res.data[0] if res.data else None

    def find_by_bot_token_hash(self, token_hash: str) -> dict | None:
        """Lookup de la casa por hash del bot_token. Usado en bot_auth."""
        res = supabase.table("houses").select("*").eq("bot_token_hash", token_hash).execute()
        return res.data[0] if res.data else None

class FloorRepository:

    def find_by_house(self, house_id: str) -> list[dict]:
        res = (
            supabase.table("floors")
            .select("*")
            .eq("house_id", house_id)
            .order("created_at")
            .execute()
        )
        return res.data or []

    def find_by_ids(self, floor_ids: list[str]) -> list[dict]:
        if not floor_ids:
            return []
        return (
            supabase.table("floors")
            .select("id,name")
            .in_("id", floor_ids)
            .execute()
            .data
            or []
        )


class RoomRepository:

    def find_by_floor(self, floor_id: str) -> list[dict]:
        res = supabase.table("rooms").select("*").eq("floor_id", floor_id).execute()
        return res.data or []

    def find_ids_by_floor(self, floor_id: str) -> list[str]:
        res = supabase.table("rooms").select("id").eq("floor_id", floor_id).execute()
        return [r["id"] for r in (res.data or [])]

    def find_by_ids(self, room_ids: list[str]) -> list[dict]:
        if not room_ids:
            return []
        return (
            supabase.table("rooms")
            .select("id,name,floor_id")
            .in_("id", room_ids)
            .execute()
            .data
            or []
        )


class HouseMemberRepository:

    def find_house_id_by_user(self, user_id: str) -> str | None:
        res = (
            supabase.table("house_members")
            .select("house_id")
            .eq("user_id", user_id)
            .execute()
        )
        return res.data[0]["house_id"] if res.data else None

    def find_role(self, house_id: str, user_id: str) -> str | None:
        res = (
            supabase.table("house_members")
            .select("role")
            .eq("house_id", house_id)
            .eq("user_id", user_id)
            .execute()
        )
        return res.data[0]["role"] if res.data else None

    def find_user_ids_by_house(self, house_id: str) -> list[str]:
        res = (
            supabase.table("house_members")
            .select("user_id")
            .eq("house_id", house_id)
            .execute()
        )
        return [m["user_id"] for m in (res.data or [])]

    def find_members_by_house(self, house_id: str) -> list[dict]:
        res = (
            supabase.table("house_members")
            .select("user_id, role, created_at")
            .eq("house_id", house_id)
            .execute()
        )
        return res.data or []

class HouseInvitationRepository:

    def find_unused_by_code(self, code: str) -> dict | None:
        res = (
            supabase.table("house_invitations")
            .select("*")
            .eq("code", code.upper())
            .is_("used_at", "null")
            .execute()
        )
        return res.data[0] if res.data else None


house_repository            = HouseRepository()
floor_repository            = FloorRepository()
room_repository             = RoomRepository()
house_member_repository     = HouseMemberRepository()
house_invitation_repository = HouseInvitationRepository()
