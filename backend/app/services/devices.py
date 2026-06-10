import json
import requests
from fastapi import HTTPException, status

from app.core.db import supabase
from app.core.config import settings
from app.core.errors import bad_request, conflict, not_found
from app.models.devices import DeviceVincular, DeviceStatusUpdate, HAConnectSchema
from app.services.xmpp import send_xmpp_message
from app.services.home import get_house_id_for_user, get_user_role, get_bot_target_for_user, require_owner
from app.services.command_executor import execute_command, CommandSource
from app.repositories.devices import device_repository
from app.repositories.ha_integrations import ha_integration_repository
from app.repositories.users import xmpp_account_repository
from app.repositories.houses import room_repository
from app.models.drivers import DriverType


def _detectar_driver_tv(hostname: str) -> DriverType | None:
    hostname = hostname.lower()
    if "lg" in hostname:
        return DriverType.LG_TV
    if "samsung" in hostname:
        return DriverType.SAMSUNG_TV
    return None


def inferir_driver(tipo: str, hostname: str = "") -> DriverType | None:
    mapa = {
        "SmartTV":    lambda: _detectar_driver_tv(hostname),
        "Enchufe":    lambda: DriverType.TUYA,
        "light":      lambda: DriverType.TUYA,
        "switch":     lambda: DriverType.TUYA,
        "climate":    lambda: DriverType.TUYA,
        "Luz":        lambda: DriverType.TUYA,
        "IoT":        lambda: DriverType.TUYA,
        "Termostato": lambda: DriverType.TUYA,
        "Sensor":     lambda: DriverType.TUYA,   
        "sensor":     lambda: DriverType.TUYA,
    }
    fn = mapa.get(tipo)
    return fn() if fn else None


def inferir_config(tipo: str) -> dict:
    if tipo in ("Luz", "IoT", "Termostato", "Enchufe", "light", "switch"):
        return {"channel": 0}
    return {}


def vincular_device(device_in: DeviceVincular, user_id: str) -> dict:
    driver = device_in.driver or inferir_driver(device_in.tipo, device_in.hostname or "") or DriverType.GENERIC
    config = device_in.config or inferir_config(device_in.tipo)
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise bad_request("El usuario no tiene una casa asociada")

    try:
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
    except Exception as e:
        msg = str(e)
        if "house_id_name" in msg or "unique" in msg.lower():
            raise conflict("Ya existe un dispositivo con ese nombre en esta casa")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, msg)

    if not result.data:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error al vincular dispositivo")
    return result.data[0]


def get_devices_for_house(house_id: str) -> list[dict]:
    devices = device_repository.find_by_house(house_id)

    ha_devices = [d for d in devices if d.get("driver") == DriverType.HOMEASSISTANT]
    if ha_devices:
        creds = ha_integration_repository.find_credentials_by_house(house_id)
        if creds:
            for d in ha_devices:
                d["config"] = {
                    "ha_url":    creds["ha_url"],
                    "token":     creds["token"],
                    "entity_id": d["ha_entity_id"],
                }

    return devices


def get_devices(user_id: str) -> list[dict]:
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return []
    return device_repository.find_by_house(house_id)


def get_device(device_id: str, user_id: str) -> dict | None:
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return None
    return device_repository.find_by_id_and_house(device_id, house_id)


def desvincular_device(device_id: str, user_id: str) -> bool:
    if get_user_role(user_id) == "owner":
        house_id = get_house_id_for_user(user_id)
        if not house_id:
            return False
        result = supabase.table("devices").delete().eq("id", device_id).eq("house_id", house_id).execute()
    else:
        result = supabase.table("devices").delete().eq("id", device_id).eq("owner_id", user_id).execute()
    return bool(result.data)


def update_device(device_id: str, user_id: str, data: dict) -> dict | None:
    if get_user_role(user_id) == "owner":
        house_id = get_house_id_for_user(user_id)
        if not house_id:
            return None
        result = supabase.table("devices").update(data).eq("id", device_id).eq("house_id", house_id).execute()
    else:
        result = supabase.table("devices").update(data).eq("id", device_id).eq("owner_id", user_id).execute()
    return result.data[0] if result.data else None


def update_device_status_in_house(device_id: str, house_id: str, status_in: DeviceStatusUpdate) -> bool:
    data: dict = {"is_online": status_in.is_online, "updated_at": "now()"}
    if status_in.estado:
        data["estado"] = status_in.estado
    result = (
        supabase.table("devices").update(data)
        .eq("id", device_id).eq("house_id", house_id)
        .execute()
    )
    return bool(result.data)

def find_devices_in_scope(scope: str, scope_id: str, fields: str = "id") -> list[dict]:
    if scope == "room":
        devices = device_repository.find_by_room(scope_id, fields)
        if not devices:
            raise not_found("No hay dispositivos en esta habitación")
        return devices
    if scope == "floor":
        room_ids = room_repository.find_ids_by_floor(scope_id)
        if not room_ids:
            raise not_found("No hay habitaciones en esta planta")
        devices = device_repository.find_by_rooms(room_ids, fields)
        if not devices:
            raise not_found("No hay dispositivos en esta planta")
        return devices
    raise bad_request(f"Scope inválido: {scope}")


async def send_group_command(scope: str, scope_id: str, action: str, user_id: str) -> dict:
    """Send a power action ('encender'/'apagar') to every device in a room or floor."""
    if action not in ("encender", "apagar"):
        raise bad_request("Solo se permiten acciones 'encender' o 'apagar'")
    devices = find_devices_in_scope(scope, scope_id)
    results = []
    for d in devices:
        try:
            r = await execute_command(
                action=action,
                payload={},
                user_id=user_id,
                source=CommandSource(source_type="direct"),
                device_id=d["id"],
            )
            results.append({"device_id": d["id"], "command_id": r["command_id"]})
        except Exception:
            results.append({"device_id": d["id"], "error": "No se pudo enviar"})
    return {"ok": True, "results": results}


async def request_device_poll(device_id: str, user_id: str) -> None:
    """Ask the bot to do an immediate get_status() on a newly linked device."""
    try:
        jid = xmpp_account_repository.find_jid_by_user(user_id)
        if not jid:
            return
        password_result = supabase.rpc("get_xmpp_password", {
            "p_user_id": user_id,
            "p_key": settings.XMPP_ENCRYPTION_KEY
        }).execute()
        xmpp_password = password_result.data
        bot_target = get_bot_target_for_user(user_id)
        if not bot_target:
            return
        await send_xmpp_message(
            body=json.dumps({"type": "poll_device", "device_id": device_id}),
            from_jid=jid,
            xmpp_password=xmpp_password,
            to_jid=bot_target,
        )
    except Exception:
        pass  # Non-critical — device will be polled on next cycle


def update_device_config_in_house(device_id: str, house_id: str, config: dict) -> None:
    """Update config solo si el device pertenece a esa casa (autorización por bot_token).
    Usado por drivers (LG TV) para guardar client_key tras pairing."""
    supabase.table("devices").update({"config": config}) \
        .eq("id", device_id).eq("house_id", house_id).execute()


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


def _import_ha_states(house_id: str, owner_id: str, ha_url: str, token: str) -> int:
    """Fetch /api/states de HA y hace upsert de cada entidad útil en devices.
    Devuelve cuántas se importaron."""
    r = requests.get(
        f"{ha_url}/api/states",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5
    )
    entidades = r.json()

    tipos_utiles = ("light.", "switch.", "climate.", "media_player.")
    mac_map      = _ha_entity_mac_map(ha_url, token)
    importados   = 0

    for e in entidades:
        if not e["entity_id"].startswith(tipos_utiles):
            continue

        supabase.table("devices").upsert({
            "owner_id":     owner_id,
            "house_id":     house_id,
            "name":         e["attributes"].get("friendly_name", e["entity_id"]),
            "type":         e["entity_id"].split(".")[0],
            "driver":       DriverType.HOMEASSISTANT,
            "ha_entity_id": e["entity_id"],
            "mac":          mac_map.get(e["entity_id"]),
            "config":       {},
        }, on_conflict="house_id,ha_entity_id").execute()

        importados += 1
    return importados


def connect_ha(user_id: str, data: HAConnectSchema) -> dict:
    """Owner-only: guarda credenciales HA en la casa e importa la lista de entidades."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise bad_request("El usuario no tiene una casa asociada")
    require_owner(user_id)

    try:
        r = requests.get(
            f"{data.ha_url}/api/",
            headers={"Authorization": f"Bearer {data.token}"},
            timeout=5
        )
        r.raise_for_status()
    except Exception:
        raise bad_request("No se pudo conectar con Home Assistant")

    supabase.table("ha_integrations").upsert({
        "house_id": house_id,
        "ha_url":   data.ha_url,
        "token":    data.token
    }, on_conflict="house_id").execute()

    importados = _import_ha_states(house_id, user_id, data.ha_url, data.token)
    return {"ok": True, "importados": importados}


# ── Status (bot/webhook) ─────────────────────────────────────────────────────
def get_status_for_bot_in_house(device_id: str, house_id: str) -> dict:
    """Bot read: snapshot del estado de un device. Solo si pertenece a esa casa."""
    d = device_repository.find_by_id_and_house(device_id, house_id)
    if not d:
        raise not_found("Dispositivo no encontrado")
    return {
        "device_id":   d["id"],
        "is_online":   d.get("is_online"),
        "estado":      d.get("estado") or {},
        "last_update": d.get("updated_at"),
    }


# ── Home Assistant integration management ───────────────────────────────────
def get_ha_connection(user_id: str) -> dict:
    """Return HA connection info for the caller's house, or {connected: False}."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return {"connected": False}
    row = ha_integration_repository.find_summary_by_house(house_id)
    if not row:
        return {"connected": False}
    return {"connected": True, "ha_url": row["ha_url"], "created_at": row["created_at"]}


def reimport_ha(user_id: str) -> dict:
    """Any member can reimport: refresca la lista de devices usando las credenciales
    guardadas en la casa. Raises HAConnectionMissing si la casa no tiene integración."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise not_found("No hay integración de Home Assistant configurada")
    stored = ha_integration_repository.find_credentials_by_house(house_id)
    if not stored:
        raise not_found("No hay integración de Home Assistant configurada")
    importados = _import_ha_states(house_id, user_id, stored["ha_url"], stored["token"])
    return {"ok": True, "importados": importados}


def disconnect_ha(user_id: str) -> None:
    """Owner-only: remove the house's HA integration and all its HA-imported devices."""
    house_id = get_house_id_for_user(user_id)
    if not house_id:
        return
    require_owner(user_id)
    supabase.table("ha_integrations").delete().eq("house_id", house_id).execute()
    (
        supabase.table("devices")
        .delete()
        .eq("house_id", house_id)
        .eq("driver", DriverType.HOMEASSISTANT)
        .execute()
    )