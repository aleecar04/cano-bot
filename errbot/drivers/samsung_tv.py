import time
from wakeonlan import send_magic_packet
from .base import BaseDriver
from .actions_catalog import Action

# pip install samsungtvws
try:
    from samsungtvws import SamsungTVWS
    SAMSUNG_AVAILABLE = True
except ImportError:
    SAMSUNG_AVAILABLE = False

# Samsung Tizen app IDs
SAMSUNG_APPS = {
    "netflix": "11101200001",
    "youtube": "111299001912",
    "prime":   "3201910019365",
}

# Direct key codes for common apps (faster than launching via app ID)
SAMSUNG_APP_KEYS = {
    "netflix": "KEY_NETFLIX",
}


class SamsungTVDriver(BaseDriver):

    def _tv(self, device: dict) -> "SamsungTVWS":
        if not SAMSUNG_AVAILABLE:
            raise RuntimeError("samsungtvws no instalado. Ejecuta: pip install samsungtvws")
        config = device.get("config") or {}
        token = config.get("token")
        return SamsungTVWS(
            host=device["ip"],
            token=token,
            token_file=None,
        )

    def _send_key(self, device: dict, key: str) -> dict:
        try:
            tv = self._tv(device)
            tv.send_key(key)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_status(self, device: dict, timeout: float = 2.0) -> dict:
        try:
            start = time.time()
            tv = self._tv(device)
            info = tv.rest_device_info()
            if time.time() - start > timeout:
                return {"is_online": False}
            power_on = info.get("device", {}).get("PowerState", "off") == "on"
            return {
                "is_online": True,
                "estado": {"power": "on" if power_on else "off"}
            }
        except Exception:
            return {"is_online": False}

    def encender(self, device: dict) -> dict:
        mac = device.get("mac")
        if not mac:
            return {"ok": False, "error": "MAC no configurada para Wake on LAN"}
        try:
            send_magic_packet(mac)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def apagar(self, device: dict) -> dict:
        return self._send_key(device, "KEY_POWER")

    def set_volumen(self, device: dict, valor: int) -> dict:
        # Samsung doesn't support absolute volume via WebSocket — step to target
        try:
            tv = self._tv(device)
            current = tv.rest_device_info().get("device", {}).get("Volume", 0)
            target = max(0, min(100, valor))
            diff = target - int(current)
            key = "KEY_VOLUMEUP" if diff > 0 else "KEY_VOLUMEDOWN"
            for _ in range(abs(diff)):
                tv.send_key(key)
            return {"ok": True, "volumen": target}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def abrir_app(self, device: dict, app: str) -> dict:
        key = SAMSUNG_APP_KEYS.get(app.lower())
        if key:
            return self._send_key(device, key)
        app_id = SAMSUNG_APPS.get(app.lower(), app)
        try:
            tv = self._tv(device)
            tv.run_app(app_id)
            return {"ok": True, "app": app}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def ejecutar(self, device: dict, accion: str, payload: dict = {}) -> dict:
        extras = {
            Action.SUBIR_VOLUMEN: lambda: self._send_key(device, "KEY_VOLUMEUP"),
            Action.BAJAR_VOLUMEN: lambda: self._send_key(device, "KEY_VOLUMEDOWN"),
            Action.MUTE:          lambda: self._send_key(device, "KEY_MUTE"),
            Action.SET_VOLUMEN:   lambda: self.set_volumen(device, int(payload.get("valor", 50))),
            Action.ABRIR_APP:     lambda: self.abrir_app(device, str(payload.get("app", ""))),
        }
        if accion in extras:
            return extras[accion]()
        return super().ejecutar(device, accion, payload)
