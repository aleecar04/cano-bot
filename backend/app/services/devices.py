import json
import requests
from pydantic import BaseModel
from app.core.db import supabase
from app.core.config import settings
from app.models import DeviceVincular, DeviceStatusUpdate, CommandCreate
from app.services.xmpp import send_xmpp_message


def _detectar_driver_tv(hostname: str) -> str:
    hostname = hostname.lower()
    if "lg" in hostname:
        return "lg_tv"
    # Samsung TVs use Tizen OS; most modern ones support ADB like Android TV
    if "samsung" in hostname:
        return "android_tv"
    return "android_tv"


def inferir_driver(tipo: str, hostname: str = "") -> str | None:
    mapa = {
        "SmartTV":    lambda: _detectar_driver_tv(hostname),
        "light":      lambda: "tuya",
        "switch":     lambda: "tuya",
        "climate":    lambda: "tuya",
        "Luz":        lambda: "tuya",
        "IoT":        lambda: "tuya",
        "Termostato": lambda: "tuya",
        "Altavoz":    lambda: "tuya",
    }
    fn = mapa.get(tipo)
    return fn() if fn else None


def inferir_config(tipo: str) -> dict:
    if tipo in ("Luz", "IoT", "Termostato", "light", "switch"):
        return {"channel": 0}
    return {}


def vincular_device(device_in: DeviceVincular, user_id: str) -> dict:
    driver = device_in.driver or inferir_driver(device_in.tipo, device_in.hostname or "") or "generic"

    config = device_in.config or inferir_config(device_in.tipo)

    result = supabase.table("devices").upsert({
        "owner_id":  user_id,
        "name":      device_in.name,
        "type":      device_in.tipo,
        "driver":    driver,
        "ip":        device_in.ip,
        "mac":       device_in.mac,
        "config":    config,
        "is_online": False,
        "room_id":   str(device_in.room_id) if device_in.room_id else None,
    }, on_conflict="owner_id,mac").execute()
    

    if not result.data:
        raise RuntimeError("Error al vincular dispositivo")
    return result.data[0]


def get_all_devices(owner_id: str | None = None) -> list[dict]:
    """Returns devices for the bot. Optionally filtered by owner."""
    query = supabase.table("devices").select("*")
    if owner_id:
        query = query.eq("owner_id", owner_id)
    return query.execute().data or []


def get_devices(user_id: str) -> list[dict]:
    result = supabase.table("devices")\
        .select("*")\
        .eq("owner_id", user_id)\
        .execute()
    return result.data


def get_device(device_id: str, user_id: str) -> dict | None:
    result = supabase.table("devices")\
        .select("*")\
        .eq("id", device_id)\
        .eq("owner_id", user_id)\
        .execute()
    return result.data[0] if result.data else None


def desvincular_device(device_id: str, user_id: str) -> bool:
    result = supabase.table("devices")\
        .delete()\
        .eq("id", device_id)\
        .eq("owner_id", user_id)\
        .execute()
    return bool(result.data)


def update_device_status(device_id: str, status_in: DeviceStatusUpdate) -> bool:
    result = supabase.table("devices").update({
        "is_online":  status_in.is_online,
        "estado":     status_in.estado,
        "updated_at": "now()",       # ← last_seen_at eliminado
    }).eq("id", device_id).execute()
    return bool(result.data)

def get_device_status_for_sync(device_id: str) -> dict | None:
    result = supabase.table("devices")\
        .select("id, is_online, estado, updated_at")\
        .eq("id", device_id)\
        .execute()
    return result.data[0] if result.data else None


async def send_command(device_id: str, command_in: CommandCreate, user_id: str) -> dict:
    device = get_device(device_id, user_id)
    if not device:
        raise ValueError("Dispositivo no encontrado")

    jid_result = supabase.table("xmpp_accounts")\
        .select("jid")\
        .eq("user_id", user_id)\
        .execute()
    if not jid_result.data:
        raise ValueError("Usuario XMPP no encontrado")

    jid = jid_result.data[0]["jid"]
    password_result = supabase.rpc("get_xmpp_password", {
        "p_user_id": user_id,
        "p_key": settings.XMPP_ENCRYPTION_KEY
    }).execute()
    xmpp_password = password_result.data

    cmd = supabase.table("commands").insert({
        "user_id":   user_id,
        "device_id": device_id,
        "action":    command_in.accion,
        "payload":   command_in.payload,
        "status":    "pending",
    }).execute().data[0]

    await send_xmpp_message(
        body=json.dumps({
            "device_id":  device_id,
            "accion":     command_in.accion,
            "payload":    command_in.payload,
            "command_id": cmd["id"],
        }),
        from_jid=jid,
        xmpp_password=xmpp_password
    )
    return {"ok": True, "command_id": cmd["id"]}


def update_device_config(device_id: str, config: dict) -> None:
    supabase.table("devices").update({
        "config": config
    }).eq("id", device_id).execute()


class HAConnectSchema(BaseModel):
    ha_url: str
    token: str


def connect_ha(user_id: str, data: HAConnectSchema) -> dict:
    try:
        r = requests.get(
            f"{data.ha_url}/api/",
            headers={"Authorization": f"Bearer {data.token}"},
            timeout=5
        )
        r.raise_for_status()
    except Exception:
        raise ValueError("No se pudo conectar con Home Assistant")

    supabase.table("ha_integrations").upsert({
        "user_id": user_id,
        "ha_url":  data.ha_url,
        "token":   data.token
    }, on_conflict="user_id").execute()

    r = requests.get(
        f"{data.ha_url}/api/states",
        headers={"Authorization": f"Bearer {data.token}"},
        timeout=5
    )
    entidades = r.json()

    tipos_utiles = ("light.", "switch.", "climate.", "cover.", "media_player.")
    importados = 0

    for e in entidades:
        if not e["entity_id"].startswith(tipos_utiles):
            continue

        supabase.table("devices").upsert({
            "owner_id":     user_id,
            "name":         e["attributes"].get("friendly_name", e["entity_id"]),
            "type":         e["entity_id"].split(".")[0],
            "driver":       "homeassistant",
            "ha_entity_id": e["entity_id"],
            "config": {
                "entity_id": e["entity_id"],
                "ha_url":    data.ha_url,
                "token":     data.token
            }
        }, on_conflict="owner_id,ha_entity_id").execute()

        importados += 1

    return {"ok": True, "importados": importados}