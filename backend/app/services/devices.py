import json
from fastapi import HTTPException, status

from app.core.db import supabase
from app.core.config import settings
from app.core.errors import bad_request, conflict, not_found
from app.models.devices import DeviceVincular, DeviceStatusUpdate, HAConnectSchema
from app.services.xmpp import xmpp_service
from app.services.home import home_service
from app.services.command_executor import execute_command, CommandSource
from app.repositories.devices import device_repository
from app.repositories.ha_integrations import ha_integration_repository
from app.repositories.users import xmpp_account_repository
from app.repositories.houses import room_repository
from app.models.drivers import DriverType


def _detectar_driver_tv(hostname: str) -> DriverType | None:
    if "lg" in hostname.lower():
        return DriverType.LG_TV
    return None


# El fetch HTTP a Home Assistant lo hace el BOT (está en la red local); aquí solo
# procesamos los datos crudos que nos envía y persistimos en BD.
def _build_mac_map(entity_registry: list, device_registry: list) -> dict[str, str]:
    entity_to_device = {e["entity_id"]: e.get("device_id") for e in entity_registry}
    device_to_mac: dict[str, str] = {}
    for d in device_registry:
        for conn_type, conn_val in d.get("connections", []):
            if conn_type == "mac":
                device_to_mac[d["id"]] = conn_val
    return {
        eid: device_to_mac[did]
        for eid, did in entity_to_device.items()
        if did and did in device_to_mac
    }


def _store_ha_states(house_id: str, owner_id: str, states: list, mac_map: dict[str, str]) -> int:
    tipos_utiles = ("light.", "switch.", "climate.", "media_player.")
    importados = 0
    for e in states:
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


class DevicesService:

    def inferir_driver(self, tipo: str, hostname: str = "") -> DriverType | None:
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

    def inferir_config(self, tipo: str) -> dict:
        if tipo in ("Luz", "IoT", "Termostato", "Enchufe", "light", "switch"):
            return {"channel": 0}
        return {}

    def vincular_device(self, device_in: DeviceVincular, user_id: str) -> dict:
        driver = device_in.driver or self.inferir_driver(device_in.tipo, device_in.hostname or "") or DriverType.GENERIC
        config = device_in.config or self.inferir_config(device_in.tipo)
        house_id = home_service.get_house_id_for_user(user_id)
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
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error interno al vincular dispositivo")

        if not result.data:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Error al vincular dispositivo")
        return result.data[0]

    def get_devices_for_house(self, house_id: str) -> list[dict]:
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

    def get_devices(self, user_id: str) -> list[dict]:
        house_id = home_service.get_house_id_for_user(user_id)
        if not house_id:
            return []
        return device_repository.find_by_house(house_id)

    def get_device(self, device_id: str, user_id: str) -> dict | None:
        house_id = home_service.get_house_id_for_user(user_id)
        if not house_id:
            return None
        return device_repository.find_by_id_and_house(device_id, house_id)

    def desvincular_device(self, device_id: str, user_id: str) -> bool:
        if home_service.get_user_role(user_id) == "owner":
            house_id = home_service.get_house_id_for_user(user_id)
            if not house_id:
                return False
            result = supabase.table("devices").delete().eq("id", device_id).eq("house_id", house_id).execute()
        else:
            result = supabase.table("devices").delete().eq("id", device_id).eq("owner_id", user_id).execute()
        return bool(result.data)

    def update_device(self, device_id: str, user_id: str, data: dict) -> dict | None:
        if home_service.get_user_role(user_id) == "owner":
            house_id = home_service.get_house_id_for_user(user_id)
            if not house_id:
                return None
            result = supabase.table("devices").update(data).eq("id", device_id).eq("house_id", house_id).execute()
        else:
            result = supabase.table("devices").update(data).eq("id", device_id).eq("owner_id", user_id).execute()
        return result.data[0] if result.data else None

    def update_device_status_in_house(self, device_id: str, house_id: str, status_in: DeviceStatusUpdate) -> bool:
        data: dict = {"is_online": status_in.is_online, "updated_at": "now()"}
        if status_in.state:
            data["state"] = status_in.state
        result = (
            supabase.table("devices").update(data)
            .eq("id", device_id).eq("house_id", house_id)
            .execute()
        )
        return bool(result.data)

    def find_devices_in_scope(self, scope: str, scope_id: str, fields: str = "id") -> list[dict]:
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

    async def send_group_command(self, scope: str, scope_id: str, action: str, user_id: str) -> dict:
        if action not in ("encender", "apagar"):
            raise bad_request("Solo se permiten acciones 'encender' o 'apagar'")
        devices = self.find_devices_in_scope(scope, scope_id)
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

    async def _send_to_bot_for_user(self, user_id: str, payload: dict) -> None:
        jid = xmpp_account_repository.find_jid_by_user(user_id)
        if not jid:
            return
        password_result = supabase.rpc("get_xmpp_password", {
            "p_user_id": user_id,
            "p_key": settings.XMPP_ENCRYPTION_KEY
        }).execute()
        bot_target = home_service.get_bot_target_for_user(user_id)
        if not bot_target:
            return
        await xmpp_service.send_xmpp_message(
            body=json.dumps(payload),
            from_jid=jid,
            xmpp_password=password_result.data,
            to_jid=bot_target,
        )

    async def request_device_poll(self, device_id: str, user_id: str) -> None:
        try:
            await self._send_to_bot_for_user(user_id, {"type": "poll_device", "device_id": device_id})
        except Exception:
            pass  # Non-critical — device will be polled on next cycle

    async def _trigger_ha_import(self, user_id: str) -> None:
        # El bot (en la red local) recibirá esto, leerá las credenciales del backend,
        # hablará con HA y devolverá los estados para importarlos.
        await self._send_to_bot_for_user(user_id, {"type": "ha_import", "user_id": user_id})

    def update_device_config_in_house(self, device_id: str, house_id: str, config: dict) -> None:
        supabase.table("devices").update({"config": config}) \
            .eq("id", device_id).eq("house_id", house_id).execute()

    async def connect_ha(self, user_id: str, data: HAConnectSchema) -> dict:
        house_id = home_service.get_house_id_for_user(user_id)
        if not house_id:
            raise bad_request("El usuario no tiene una casa asociada")
        home_service.require_owner(user_id)

        # Guardamos credenciales y delegamos la conexión/importación al bot local.
        # El test de conexión y el resultado llegan de forma asíncrona (vía bot).
        supabase.table("ha_integrations").upsert({
            "house_id": house_id,
            "ha_url":   data.ha_url,
            "token":    data.token
        }, on_conflict="house_id").execute()

        await self._trigger_ha_import(user_id)
        return {"ok": True, "pending": True}

    def get_ha_credentials_for_house(self, house_id: str) -> dict:
        """Bot-only: credenciales de HA de la casa para que el bot haga el fetch local."""
        stored = ha_integration_repository.find_credentials_by_house(house_id)
        if not stored:
            raise not_found("No hay integración de Home Assistant configurada")
        return {"ha_url": stored["ha_url"], "token": stored["token"]}

    def process_ha_import(self, house_id: str, owner_id: str, states: list,
                          entity_registry: list, device_registry: list) -> int:
        """Bot-only: recibe los datos crudos de HA y los persiste como devices."""
        mac_map = _build_mac_map(entity_registry or [], device_registry or [])
        return _store_ha_states(house_id, owner_id, states or [], mac_map)

    def get_status_for_bot_in_house(self, device_id: str, house_id: str) -> dict:
        """Bot read: snapshot del estado de un device. Solo si pertenece a esa casa."""
        d = device_repository.find_by_id_and_house(device_id, house_id)
        if not d:
            raise not_found("Dispositivo no encontrado")
        return {
            "device_id":   d["id"],
            "is_online":   d.get("is_online"),
            "state":       d.get("state") or {},
            "last_update": d.get("updated_at"),
        }

    def get_ha_connection(self, user_id: str) -> dict:
        """Return HA connection info for the caller's house, or {connected: False}."""
        house_id = home_service.get_house_id_for_user(user_id)
        if not house_id:
            return {"connected": False}
        row = ha_integration_repository.find_summary_by_house(house_id)
        if not row:
            return {"connected": False}
        return {"connected": True, "ha_url": row["ha_url"], "created_at": row["created_at"]}

    async def reimport_ha(self, user_id: str) -> dict:
        house_id = home_service.get_house_id_for_user(user_id)
        stored = ha_integration_repository.find_credentials_by_house(house_id) if house_id else None
        if not stored:
            raise not_found("No hay integración de Home Assistant configurada")
        await self._trigger_ha_import(user_id)
        return {"ok": True, "pending": True}

    def disconnect_ha(self, user_id: str) -> None:
        """Owner-only: remove the house's HA integration and all its HA-imported devices."""
        house_id = home_service.get_house_id_for_user(user_id)
        if not house_id:
            return
        home_service.require_owner(user_id)
        supabase.table("ha_integrations").delete().eq("house_id", house_id).execute()
        (
            supabase.table("devices")
            .delete()
            .eq("house_id", house_id)
            .eq("driver", DriverType.HOMEASSISTANT)
            .execute()
        )


devices_service = DevicesService()


# ── Compatibilidad: alias para imports puntuales desde otros servicios ───────
# Algunos módulos (p. ej. schedules) usan find_devices_in_scope directamente.
find_devices_in_scope = devices_service.find_devices_in_scope
