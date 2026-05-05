from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_active_superuser
from app.core.db import supabase

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_active_superuser)],
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _user_map(user_ids: list[str]) -> dict:
    if not user_ids:
        return {}
    result = supabase.table("base_user").select("id,username,email").in_("id", user_ids).execute()
    return {u["id"]: u for u in (result.data or [])}


def _device_map(device_ids: list[str]) -> dict:
    if not device_ids:
        return {}
    result = supabase.table("devices").select("id,name,type").in_("id", device_ids).execute()
    return {d["id"]: d for d in (result.data or [])}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats() -> Any:
    users = supabase.table("base_user").select("id", count="exact").execute()
    devices = supabase.table("devices").select("id,is_online", count="exact").execute()
    schedules = supabase.table("schedules").select("id,is_active", count="exact").execute()
    commands = supabase.table("commands").select("id", count="exact").execute()

    online = sum(1 for d in (devices.data or []) if d.get("is_online"))
    active_schedules = sum(1 for s in (schedules.data or []) if s.get("is_active"))

    return {
        "users": users.count or 0,
        "devices": devices.count or 0,
        "devices_online": online,
        "devices_offline": (devices.count or 0) - online,
        "schedules": schedules.count or 0,
        "schedules_active": active_schedules,
        "commands": commands.count or 0,
    }


@router.get("/devices")
def get_all_devices(
    user_id: Optional[str] = Query(None),
    is_online: Optional[bool] = Query(None),
    device_type: Optional[str] = Query(None),
) -> Any:
    q = supabase.table("devices").select("*").order("registered_at", desc=True)
    if user_id:
        q = q.eq("owner_id", user_id)
    if is_online is not None:
        q = q.eq("is_online", is_online)
    if device_type:
        q = q.eq("type", device_type)

    devices = q.execute()
    if not devices.data:
        return {"data": [], "count": 0}

    # Owner info
    user_ids = list({d["owner_id"] for d in devices.data if d.get("owner_id")})
    users = _user_map(user_ids)

    # Room + floor info
    room_ids = list({d["room_id"] for d in devices.data if d.get("room_id")})
    rooms_map: dict = {}
    floors_map: dict = {}
    if room_ids:
        rooms_res = supabase.table("rooms").select("id,name,floor_id").in_("id", room_ids).execute()
        rooms_map = {r["id"]: r for r in (rooms_res.data or [])}
        floor_ids = list({r["floor_id"] for r in rooms_res.data if r.get("floor_id")})
        if floor_ids:
            floors_res = supabase.table("floors").select("id,name,level").in_("id", floor_ids).execute()
            floors_map = {f["id"]: f for f in (floors_res.data or [])}

    enriched = []
    for d in devices.data:
        room = rooms_map.get(d.get("room_id", ""))
        floor = floors_map.get(room["floor_id"]) if room else None
        enriched.append({
            **d,
            "owner": users.get(d["owner_id"]),
            "room_name": room["name"] if room else None,
            "floor_name": floor["name"] if floor else None,
        })

    return {"data": enriched, "count": len(enriched)}


@router.get("/commands")
def get_all_commands(
    user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="pending|sent|executed|failed"),
    limit: int = Query(50, le=200),
) -> Any:
    q = supabase.table("commands").select("*").order("created_at", desc=True).limit(limit)
    if user_id:
        q = q.eq("user_id", user_id)
    if status:
        q = q.eq("status", status)
    if date_from:
        q = q.gte("created_at", f"{date_from}T00:00:00")
    if date_to:
        q = q.lte("created_at", f"{date_to}T23:59:59")

    commands = q.execute()
    if not commands.data:
        return {"data": [], "count": 0}

    user_ids = list({c["user_id"] for c in commands.data if c.get("user_id")})
    device_ids = list({c["device_id"] for c in commands.data if c.get("device_id")})

    users = _user_map(user_ids)
    devices = _device_map(device_ids)

    enriched = [
        {
            **c,
            "user": users.get(c.get("user_id", "")),
            "device": devices.get(c.get("device_id", "")),
        }
        for c in commands.data
    ]
    return {"data": enriched, "count": len(enriched)}


@router.get("/schedules")
def get_all_schedules(
    user_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
) -> Any:
    q = supabase.table("schedules").select("*").order("created_at", desc=True)
    if user_id:
        q = q.eq("user_id", user_id)
    if is_active is not None:
        q = q.eq("is_active", is_active)

    schedules = q.execute()
    if not schedules.data:
        return {"data": [], "count": 0}

    user_ids = list({s["user_id"] for s in schedules.data if s.get("user_id")})
    device_ids = list({s["device_id"] for s in schedules.data if s.get("device_id")})

    users = _user_map(user_ids)
    devices = _device_map(device_ids)

    enriched = [
        {
            **s,
            "user": users.get(s.get("user_id", "")),
            "device": devices.get(s.get("device_id", "")),
        }
        for s in schedules.data
    ]
    return {"data": enriched, "count": len(enriched)}


# ── Houses ────────────────────────────────────────────────────────────────────

@router.get("/houses")
def get_all_houses():
    houses = supabase.table("houses").select("*").execute()
    result = []
    for h in (houses.data or []):
        members = supabase.table("house_members").select("user_id,role").eq("house_id", h["id"]).execute()
        owner_ids = [m["user_id"] for m in (members.data or []) if m["role"] == "owner"]
        owner = None
        if owner_ids:
            u = supabase.table("base_user").select("username,email").eq("id", owner_ids[0]).execute()
            owner = u.data[0] if u.data else None
        result.append({
            **h,
            "member_count": len(members.data or []),
            "owner": owner,
        })
    return {"data": result, "count": len(result)}


@router.delete("/houses/{house_id}", status_code=204)
def delete_house(house_id: str):
    result = supabase.table("houses").delete().eq("id", house_id).execute()
    if not result.data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Casa no encontrada")
