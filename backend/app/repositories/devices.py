import unicodedata

from app.core.db import supabase

_NAME_STOPWORDS = {"el", "la", "los", "las", "del", "de", "en", "mi", "mis", "un", "una"}


def _normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    return " ".join(s.split())


def match_device_by_name(name: str, devices: list[dict]) -> dict | None:
    q = _normalize_name(name)
    if not q or not devices:
        return None
    for d in devices:
        n = _normalize_name(d.get("name", ""))
        if q in n or n in q:
            return d
    q_tokens = {t for t in q.split() if t not in _NAME_STOPWORDS}
    best, best_score = None, 0
    for d in devices:
        n_tokens = {t for t in _normalize_name(d.get("name", "")).split() if t not in _NAME_STOPWORDS}
        score = len(q_tokens & n_tokens)
        if score > best_score:
            best, best_score = d, score
    return best if best_score > 0 else None


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
        devices = (
            supabase.table("devices")
            .select("*")
            .eq("house_id", house_id)
            .execute()
            .data
        ) or []
        return match_device_by_name(name, devices)

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
