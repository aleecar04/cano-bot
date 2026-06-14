import json
import threading
from errbot import BotPlugin, botcmd

from plugins._core import BasePlugin
from plugins._helpers import (
    get_device,
    calculate_expected_state,
)
from plugins.device_cache import device_cache
from api import is_backend_reachable
from api import devices as api_devices
from drivers import execute_command, get_status


_PATCH_TIMEOUT_S = 5
_VERIFY_DELAY_S = 1.5

# Claves del estado que cada acción modifica. Se usan para comparar
# solo lo relevante durante la verificación post-acción.
_ACTION_TO_KEYS: dict[str, tuple[str, ...]] = {
    "encender":          ("power",),
    "apagar":            ("power",),
    "brillo":            ("brightness",),
    "temperatura_color": ("color_temp", "work_mode"),
    "color_rgb":         ("color_hex", "work_mode"),
    "subir_volumen":     ("volume",),
    "bajar_volumen":     ("volume",),
    "mute":              ("volume",),
    "set_volumen":       ("volume",),
}


def _patch_device_status(device_id: str, is_online: bool, state: dict) -> None:
    if not is_backend_reachable():
        return
    try:
        api_devices.patch_status(device_id, is_online, state, timeout=_PATCH_TIMEOUT_S)
    except Exception:
        pass


def _states_match(predicted: dict, real: dict, action: str) -> bool:
    """Compara solo las claves que la acción tenía que modificar."""
    keys = _ACTION_TO_KEYS.get(action, ())
    return all(predicted.get(k) == real.get(k) for k in keys)


class Control(BasePlugin, BotPlugin):

    @botcmd
    def control_device(self, msg, args):
        try:
            data = json.loads(args)
            device = get_device(data["device_id"])
            if not device:
                return {"ok": False, "error": "Dispositivo no encontrado"}

            result = execute_command(device, data["action"], data.get("payload", {}))
            self._sync_after_action(device, data["action"], data.get("payload", {}), result)
            return result

        except Exception as e:
            self.log.error(f"Error in control_device: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}

    def _sync_after_action(self, device: dict, action: str, payload: dict, result: dict) -> None:
        """Actualiza cache + backend tras ejecutar una acción y programa
        una verificación asíncrona del estado real (patrón optimista con
        reconciliación)."""
        device_id = device["id"]
        if result.get("ok"):
            predicted = calculate_expected_state(device, action, payload)
            device_cache.update(device_id, state=predicted, is_online=True)
            _patch_device_status(device_id, is_online=True, state=predicted)
            # Reconciliación asíncrona: confirma o corrige la predicción
            timer = threading.Timer(
                _VERIFY_DELAY_S,
                self._verify_state,
                args=(device, action, predicted),
            )
            timer.daemon = True
            timer.start()
        else:
            old = device_cache.get(device_id)
            old_state = old.state if old else {}
            device_cache.mark_offline(device_id)
            _patch_device_status(device_id, is_online=False, state=old_state)

    def _verify_state(self, device: dict, action: str, predicted: dict) -> None:
        """Consulta el estado real al dispositivo y, si difiere del estado
        predicho en alguna de las claves modificadas por la acción, propaga
        el estado real al backend. Silencia errores: el polling periódico
        actúa como red de seguridad si la verificación falla."""
        try:
            result = get_status(device)
            real_state = result.get("state") if isinstance(result, dict) else None
            if real_state and not _states_match(predicted, real_state, action):
                device_cache.update(device["id"], state=real_state, is_online=True)
                _patch_device_status(device["id"], is_online=True, state=real_state)
        except Exception:
            pass

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
            "state":     cached.state     if cached else (device.get("state") or {}),
        }
