from datetime import datetime, timezone

from app.core.db import supabase

_TTL_S = 90.0


def mark_seen(house_id: str) -> None:
    supabase.table("houses").update(
        {"bot_last_seen": datetime.now(timezone.utc).isoformat()}
    ).eq("id", house_id).execute()


def is_online(house_id: str) -> bool:
    res = (
        supabase.table("houses")
        .select("bot_last_seen")
        .eq("id", house_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return False
    ts = res.data[0].get("bot_last_seen")
    if not ts:
        return False
    try:
        last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False
    return (datetime.now(timezone.utc) - last).total_seconds() < _TTL_S
