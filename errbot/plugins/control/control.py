import json
from errbot import BotPlugin, botcmd

from plugins._core import BasePlugin
from plugins._helpers import (
    get_device,
    calculate_expected_state,
)
from plugins.device_cache import device_cache
from api import is_backend_reachable
from api import devices as api_devices
from drivers import ejecutar_comando


_PATCH_TIMEOUT_S = 5


def _patch_device_status(device_id: str, is_online: bool, estado: dict) -> None:
    """Best-effort PATCH /devices/{id}/status. Si falla, el próximo poll lo recupera."""
    if not is_backend_reachable():
        return
    try:
        api_devices.patch_status(device_id, is_online, estado, timeout=_PATCH_TIMEOUT_S)
    except Exception:
        pass


class Control(BasePlugin, BotPlugin):

    @botcmd
    def control_device(self, msg, args):
        """Ejecuta un comando sobre un device. `args` es JSON con device_id, action, payload.
        Devuelve dict con el resultado (lo consume el dispatcher directamente)."""
        try:
            data = json.loads(args)
            device = get_device(data["device_id"])
            if not device:
                return {"ok": False, "error": "Dispositivo no encontrado"}

            result = ejecutar_comando(device, data["action"], data.get("payload", {}))
            self._sync_after_action(device, data["action"], data.get("payload", {}), result)
            return result

        except Exception as e:
            self.log.error(f"Error in control_device: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}

    def _sync_after_action(self, device: dict, action: str, payload: dict, result: dict) -> None:
        """Actualiza cache + backend tras ejecutar una acción."""
        device_id = device["id"]
        if result.get("ok"):
            new_state = calculate_expected_state(device, action, payload)
            device_cache.update(device_id, estado=new_state, is_online=True)
            _patch_device_status(device_id, is_online=True, estado=new_state)
        else:
            old = device_cache.get(device_id)
            old_state = old.estado if old else {}
            device_cache.mark_offline(device_id)
            _patch_device_status(device_id, is_online=False, estado=old_state)

    @botcmd
    def list_devices(self, msg, args):
        """Devuelve (dict) la lista de dispositivos de la casa con su estado actual,
        que el dispatcher guarda en command.result_data."""
        try:
            devices = api_devices.get_all()
            return {
                "tipo":         "device_list",
                "dispositivos": [self._serialize_device(d) for d in devices],
                "total":        len(devices),
            }
        except Exception as e:
            return {"tipo": "error", "mensaje": str(e)}

    @staticmethod
    def _serialize_device(device: dict) -> dict:
        """Combina la fila del backend con el cache local (si lo hay)."""
        cached = device_cache.get(device["id"])
        return {
            "id":        device["id"],
            "name":      device["name"],
            "type":      device["type"],
            "driver":    device["driver"],
            "is_online": cached.is_online if cached else device.get("is_online", False),
            "estado":    cached.estado    if cached else (device.get("estado") or {}),
        }
