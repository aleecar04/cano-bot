"""
Shelly Gen1 driver — covers ALL device families emulated by fake-shelly.

Device type (stored in DB) determines the endpoint family:
  Enchufe / IoT  → /relay/{idx}          (SHPLG-S, SHSW-1, SHSW-PM, SHSW-44)
  Luz (bulb/dim) → /light/0              (SHBLB-1, SHDM-1)
  Luz RGB        → /color/0              (SHRGBW2, config.shelly_model=SHRGBW2)
  Persiana       → /roller/0             (SHSW-21/25 in roller mode)
  Sensor         → /status read-only     (SHHT-1, SHWT-1, SHSEN-1)

Test with fake-shelly:
  bin/fake-shelly SHPLG-S    → Enchufe
  bin/fake-shelly SHRGBW2    → Luz RGB
  bin/fake-shelly SHBLB-1    → Luz bombilla
  bin/fake-shelly SHDM-1     → Luz regulable
  bin/fake-shelly SHHT-1     → Sensor temperatura/humedad
  bin/fake-shelly SHWT-1     → Sensor inundacion
  bin/fake-shelly SHSEN-1    → Sensor puerta/ventana
  bin/fake-shelly SHSW-21    → Enchufe doble / Persiana
"""

import requests
from .base import BaseDriver

_LUZ_TYPES    = frozenset({"Luz", "light"})
_SENSOR_TYPES = frozenset({"Sensor", "sensor"})
_COVER_TYPES  = frozenset({"Persiana", "cover"})


class ShellyDriver(BaseDriver):

    def _url(self, device: dict, path: str) -> str:
        ip   = device["ip"]
        port = device.get("config", {}).get("port", 80)
        base = f"http://{ip}" if port == 80 else f"http://{ip}:{port}"
        return f"{base}{path}"

    def _relay_idx(self, device: dict) -> int:
        return int(device.get("config", {}).get("relay_index", 0))

    def _is_rgb(self, device: dict) -> bool:
        return str(device.get("config", {}).get("shelly_model", "")).upper() == "SHRGBW2"

    def _light_path(self, device: dict) -> str:
        return "/color/0" if self._is_rgb(device) else "/light/0"

    # ── Status ───────────────────────────────────────────────────────────────────

    def get_status(self, device: dict, timeout: float = 2.0) -> dict:
        tipo = device.get("type", "")
        try:
            r = requests.get(self._url(device, "/status"), timeout=timeout)
            r.raise_for_status()
            data = r.json()

            if tipo in _SENSOR_TYPES:
                estado: dict = {}
                if "tmp" in data:
                    estado["temperature"] = round(data["tmp"].get("value", 0), 1)
                if "hum" in data:
                    estado["humidity"] = int(data["hum"].get("value", 0))
                if "flood" in data:
                    estado["flood"] = data["flood"]
                if "sensor" in data:
                    estado["door"] = data["sensor"].get("state", "unknown")
                return {"is_online": True, "estado": estado}

            if tipo in _COVER_TYPES:
                rollers = data.get("rollers", [{}])
                state   = rollers[0].get("state", "stop") if rollers else "stop"
                pos     = rollers[0].get("current_pos", 0) if rollers else 0
                return {"is_online": True, "estado": {"power": "on" if state != "stop" else "off", "position": pos}}

            if tipo in _LUZ_TYPES:
                lights = data.get("lights", [{}])
                is_on  = lights[0].get("ison", False) if lights else False
                brightness = lights[0].get("brightness", 100) if lights else 100
                return {"is_online": True, "estado": {"power": "on" if is_on else "off", "brightness": brightness}}

            # Default: relay (Enchufe, IoT)
            relays  = data.get("relays", [])
            idx     = self._relay_idx(device)
            is_on   = relays[idx]["ison"] if idx < len(relays) else False
            power_w = relays[idx].get("power", 0) if idx < len(relays) else 0
            return {"is_online": True, "estado": {"power": "on" if is_on else "off", "power_w": power_w}}

        except Exception as e:
            return {"is_online": False, "error": str(e)}

    # ── Encender / Apagar ────────────────────────────────────────────────────────

    def encender(self, device: dict) -> dict:
        tipo = device.get("type", "")
        try:
            if tipo in _COVER_TYPES:
                r = requests.get(self._url(device, "/roller/0"), params={"go": "open"}, timeout=3)
            elif tipo in _LUZ_TYPES:
                r = requests.get(self._url(device, self._light_path(device)), params={"turn": "on"}, timeout=3)
            else:
                r = requests.get(self._url(device, f"/relay/{self._relay_idx(device)}"), params={"turn": "on"}, timeout=3)
            r.raise_for_status()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def apagar(self, device: dict) -> dict:
        tipo = device.get("type", "")
        try:
            if tipo in _COVER_TYPES:
                r = requests.get(self._url(device, "/roller/0"), params={"go": "close"}, timeout=3)
            elif tipo in _LUZ_TYPES:
                r = requests.get(self._url(device, self._light_path(device)), params={"turn": "off"}, timeout=3)
            else:
                r = requests.get(self._url(device, f"/relay/{self._relay_idx(device)}"), params={"turn": "off"}, timeout=3)
            r.raise_for_status()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Brillo ────────────────────────────────────────────────────────────────────

    def brillo(self, device: dict, valor: int) -> dict:
        if device.get("type", "") not in _LUZ_TYPES:
            return {"ok": False, "error": "Este dispositivo no soporta brillo"}
        try:
            r = requests.get(
                self._url(device, "/light/0"),
                params={"turn": "on", "brightness": max(1, min(100, valor))},
                timeout=3,
            )
            r.raise_for_status()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Color RGB (SHRGBW2) ───────────────────────────────────────────────────────

    def color_rgb(self, device: dict, r: int, g: int, b: int) -> dict:
        if device.get("type", "") not in _LUZ_TYPES or not self._is_rgb(device):
            return {"ok": False, "error": "Este dispositivo no soporta color RGB"}
        try:
            resp = requests.get(
                self._url(device, "/color/0"),
                params={"turn": "on", "red": r, "green": g, "blue": b},
                timeout=3,
            )
            resp.raise_for_status()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
