from app.core.db import supabase


class DeviceRepository:

    def find_by_house(self, house_id: str) -> list[dict]:
        return (
            supabase.table("devices")
            .select("*")
            .eq("house_id", house_id)
            .execute()
            .data
            or []
        )

    def find_by_id(self, device_id: str) -> dict | None:
        res = supabase.table("devices").select("*").eq("id", device_id).execute()
        return res.data[0] if res.data else None

    def find_by_id_and_house(self, device_id: str, house_id: str) -> dict | None:
        res = (
            supabase.table("devices")
            .select("*")
            .eq("id", device_id)
            .eq("house_id", house_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_by_name_and_house(self, name: str, house_id: str) -> dict | None:
        res = (
            supabase.table("devices")
            .select("*")
            .eq("house_id", house_id)
            .ilike("name", name)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_by_room(self, room_id: str, fields: str = "id") -> list[dict]:
        return (
            supabase.table("devices")
            .select(fields)
            .eq("room_id", room_id)
            .execute()
            .data
            or []
        )

    def find_by_rooms(self, room_ids: list[str], fields: str = "id") -> list[dict]:
        if not room_ids:
            return []
        return (
            supabase.table("devices")
            .select(fields)
            .in_("room_id", room_ids)
            .execute()
            .data
            or []
        )

    def find_by_ids(self, device_ids: list[str], fields: str = "id,name,type") -> list[dict]:
        if not device_ids:
            return []
        return (
            supabase.table("devices")
            .select(fields)
            .in_("id", device_ids)
            .execute()
            .data
            or []
        )

device_repository = DeviceRepository()
