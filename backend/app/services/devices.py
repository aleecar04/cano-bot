import json
import requests
from pydantic import BaseModel
from app.core.db import supabase
from app.core.config import settings
from app.models import DeviceVincular, DeviceStatusUpdate, CommandCreate
from app.services.xmpp import send_xmpp_message
from app.services.home import get_house_id_for_user, get_user_role


def _detectar_driver_tv(hostname: str) -> str:
    hostname = hostname.lower()
    if "lg" in hostname:
        return "lg_tv"
    if "samsung" in hostname:
        return "samsung_tv"
    return "android_tv"


_SHELLY_KEYWORDS = ("shelly", "shplg", "shsw", "shrgbw", "shblb", "shdm",
                     "shht", "shwt", "shsen", "shsw21", "shsw25")

def _is_shelly(hostname: str) -> bool:
    h = hostname.lower()
    return any(k in h for k in _SHELLY_KEYWORDS)

def _detectar_driver_enchufe(hostname: str) -> str:
    return "shelly" if _is_shelly(hostname) else "tuya"

def _detectar_driver_luz_shelly(hostname: str) -> str:
    """Shelly RGB/bulb/dimmer detected as Luz."""
    return "shelly" if _is_shelly(hostname) else "tuya"


def inferir_driver(tipo: str, hostname: str = "") -> str | None:
    # Altavoz excluded: smart speakers (Alexa, Sonos, HomePod) are not Tuya devices
    mapa = {
        "SmartTV":    lambda: _detectar_driver_tv(hostname),
        "Enchufe":    lambda: _detectar_driver_enchufe(hostname),
        "light":      lambda: "tuya",
        "switch":     lambda: "tuya",
        "climate":    lambda: "tuya",
        "Luz":        lambda: _detectar_driver_luz_shelly(hostname),
        "IoT":        lambda: "tuya",
        "Termostato": lambda: "tuya",
        "Sensor":     lambda: "tuya",      # Tuya temp/humidity sensors
        "sensor":     lambda: "tuya",
    }
    fn = mapa.get(tipo)
    return fn() if fn else None


def inferir_config(tipo: str, hostname: str = "") -> dict:
    # Simulation device: extract port from hostname (fake-shelly-{model}-{port})
    if hostname.startswith("fake-shelly-"):
        parts = hostname.rsplit("-", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return {"port": int(parts[1]), "simulated": True}
    if tipo in ("Luz", "IoT", "Termostato", "Enchufe", "light", "switch"):
        return {"channel": 0}
    return {}


def vincular_device(device_in: DeviceVincular, user_id: str) -> dict:
    driver = device_in.driver or inferir_driver(device_in.tipo, device_in.hostname or "") or "generic"
    config = device_in.config or inferir_config(device_in.tipo, device_in.hostname or "")
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise ValueError("El usuario no tiene una casa asociada")

    result = supabase.table("devices").upsert({
        "owner_id":  user_id,
        "house_id":  house_id,
        "name":      device_in.name,
        "type":      device_in.tipo,
        "driver":    driver,
        "ip":        device_in.ip,
        "mac":       device_in.mac,
        "config":    config,
        "is_online": False,
        "room_id":   str(device_in.room_id) if device_in.room_id else None,
    }, on_conflict="house_id,mac").execute()

    if not result.data:
        raise RuntimeError("Error al vincular dispositivo")
    return result.data[0]


def get_all_devices(user_id: str | None = None) -> list[dict]:
    """Bot endpoint: returns all devices for the house of the given user."""
    query = supabase.table("devices").select("*")
    if user_id:
        house_id = get_house_id_for_user(user_id)
        if house_id:
            query = query.eq("house_id", house_id)
    return query.execute().data or []


def get_devices(user_id: str) -> list[dict]:
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return []
    return supabase.table("devices").select("*").eq("house_id", house_id).execute().data or []


def get_device(device_id: str, user_id: str) -> dict | None:
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return None
    result = supabase.table("devices")\
        .select("*")\
        .eq("id", device_id)\
        .eq("house_id", house_id)\
        .execute()
    return result.data[0] if result.data else None


def desvincular_device(device_id: str, user_id: str) -> bool:
    """Owner can delete any device in the house. Member can only delete their own."""
    if get_user_role(user_id) == "owner":
        house_id = get_house_id_for_user(user_id)
        if not house_id:
            return False
        result = supabase.table("devices").delete().eq("id", device_id).eq("house_id", house_id).execute()
    else:
        result = supabase.table("devices").delete().eq("id", device_id).eq("owner_id", user_id).execute()
    return bool(result.data)


def update_device(device_id: str, user_id: str, data: dict) -> dict | None:
    """Owner can update any device in the house. Member can only update their own."""
    if get_user_role(user_id) == "owner":
        house_id = get_house_id_for_user(user_id)
        if not house_id:
            return None
        result = supabase.table("devices").update(data).eq("id", device_id).eq("house_id", house_id).execute()
    else:
        result = supabase.table("devices").update(data).eq("id", device_id).eq("owner_id", user_id).execute()
    return result.data[0] if result.data else None


def update_device_status(device_id: str, status_in: DeviceStatusUpdate) -> bool:
    data: dict = {"is_online": status_in.is_online, "updated_at": "now()"}
    if status_in.estado:
        data["estado"] = status_in.estado
    result = supabase.table("devices").update(data).eq("id", device_id).execute()
    return bool(result.data)

async def send_command(device_id: str, command_in: CommandCreate, user_id: str) -> dict:
    from app.services.command_executor import execute_command, CommandSource
    device = get_device(device_id, user_id)
    if not device:
        raise ValueError("Dispositivo no encontrado")
    return await execute_command(
        device_id=device_id,
        action=command_in.accion,
        payload=command_in.payload,
        user_id=user_id,
        source=CommandSource(source_type="direct"),
    )


async def request_device_poll(device_id: str, user_id: str) -> None:
    """Ask the bot to do an immediate get_status() on a newly linked device."""
    try:
        from app.services.home import get_bot_jid_for_user
        jid_result = supabase.table("xmpp_accounts").select("jid").eq("user_id", user_id).execute()
        if not jid_result.data:
            return
        jid = jid_result.data[0]["jid"]
        password_result = supabase.rpc("get_xmpp_password", {
            "p_user_id": user_id,
            "p_key": settings.XMPP_ENCRYPTION_KEY
        }).execute()
        xmpp_password = password_result.data
        bot_jid = get_bot_jid_for_user(user_id)
        if not bot_jid:
            return
        await send_xmpp_message(
            body=json.dumps({"type": "poll_device", "device_id": device_id}),
            from_jid=jid,
            xmpp_password=xmpp_password,
            to_jid=bot_jid,
        )
    except Exception:
        pass  # Non-critical — device will be polled on next cycle


def update_device_config(device_id: str, config: dict) -> None:
    supabase.table("devices").update({
        "config": config
    }).eq("id", device_id).execute()


class HAConnectSchema(BaseModel):
    ha_url: str
    token: str


def _ha_entity_mac_map(ha_url: str, token: str) -> dict[str, str]:
    """Devuelve {entity_id: mac} consultando el registro de HA."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        er = requests.get(f"{ha_url}/api/config/entity_registry/list", headers=headers, timeout=5)
        er.raise_for_status()
        entity_to_device = {e["entity_id"]: e.get("device_id") for e in er.json()}

        dr = requests.get(f"{ha_url}/api/config/device_registry/list", headers=headers, timeout=5)
        dr.raise_for_status()
        device_to_mac: dict[str, str] = {}
        for d in dr.json():
            for conn_type, conn_val in d.get("connections", []):
                if conn_type == "mac":
                    device_to_mac[d["id"]] = conn_val

        return {
            eid: device_to_mac[did]
            for eid, did in entity_to_device.items()
            if did and did in device_to_mac
        }
    except Exception:
        return {}


def connect_ha(user_id: str, data: HAConnectSchema) -> dict:
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise ValueError("El usuario no tiene una casa asociada")

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
    mac_map      = _ha_entity_mac_map(data.ha_url, data.token)
    importados   = 0

    for e in entidades:
        if not e["entity_id"].startswith(tipos_utiles):
            continue

        supabase.table("devices").upsert({
            "owner_id":     user_id,
            "house_id":     house_id,
            "name":         e["attributes"].get("friendly_name", e["entity_id"]),
            "type":         e["entity_id"].split(".")[0],
            "driver":       "homeassistant",
            "ha_entity_id": e["entity_id"],
            "mac":          mac_map.get(e["entity_id"]),
            "config": {
                "entity_id": e["entity_id"],
                "ha_url":    data.ha_url,
                "token":     data.token
            }
        }, on_conflict="house_id,ha_entity_id").execute()

        importados += 1

    return {"ok": True, "importados": importados}