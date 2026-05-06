import colorsys
import tinytuya
from .base import BaseDriver

_BULB_TYPES   = frozenset({"Luz", "light"})
_SENSOR_TYPES = frozenset({"Sensor", "sensor"})


def _tuya_hsv_to_hex(hsv_str: str) -> str | None:
    """Convert Tuya DPS-24 HSV hex string (12 chars) to CSS hex color (#rrggbb)."""
    try:
        h = int(hsv_str[0:4], 16) / 360.0
        s = int(hsv_str[4:8], 16) / 1000.0
        v = int(hsv_str[8:12], 16) / 1000.0
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
    except Exception:
        return None


class TuyaDriver(BaseDriver):

    def _is_bulb(self, device: dict) -> bool:
        return device.get("type", "") in _BULB_TYPES

    def _get_device(self, device: dict, timeout: float = 2.0):
        cfg = device["config"]
        kwargs = {
            "dev_id":    cfg["dev_id"],
            "address":   device["ip"],
            "local_key": cfg["local_key"],
            "version":   float(cfg.get("version", 3.4)),
        }
        dev = tinytuya.BulbDevice(**kwargs) if self._is_bulb(device) else tinytuya.Device(**kwargs)
        dev.set_socketTimeout(timeout)
        return dev

    def _is_sensor(self, device: dict) -> bool:
        return device.get("type", "") in _SENSOR_TYPES

    def get_status(self, device: dict, timeout: float = 2.0) -> dict:
        try:
            dev = self._get_device(device, timeout=timeout)
            raw = dev.status()
            if not raw or "Error" in raw:
                return {"is_online": False, "error": raw.get("Error") if raw else "no response"}
            dps = raw.get("dps", {})

            # Sensors: temperature + humidity
            if self._is_sensor(device):
                # Common Tuya sensor DPS: 1=temp(×0.1°C), 2=humidity, 4=battery
                # Some models use 101/102 instead
                temp_raw = dps.get("1") or dps.get("101")
                hum_raw  = dps.get("2") or dps.get("102")
                bat_raw  = dps.get("4") or dps.get("104")
                estado: dict = {}
                if temp_raw is not None:
                    estado["temperature"] = round(temp_raw / 10, 1)
                if hum_raw is not None:
                    estado["humidity"] = int(hum_raw)
                if bat_raw is not None:
                    estado["battery"] = int(bat_raw)
                return {"is_online": True, "estado": estado}

            # Bombillas usan DPS 20; enchufes/switches usan DPS 1
            power_dps = "20" if self._is_bulb(device) else "1"
            is_on = bool(dps.get(power_dps, False))
            estado = {"power": "on" if is_on else "off"}

            if self._is_bulb(device):
                if "21" in dps:
                    estado["work_mode"] = dps["21"]          # "white" | "colour"
                if "22" in dps:
                    estado["brightness"] = round(dps["22"] / 10)   # 10-1000 → 1-100
                if "23" in dps:
                    # Tuya 0-1000: 0=warm(2700K), 1000=cold(6500K)
                    estado["color_temp"] = round(2700 + (dps["23"] / 1000) * (6500 - 2700))
                if "24" in dps:
                    hex_color = _tuya_hsv_to_hex(str(dps["24"]))
                    if hex_color:
                        estado["color_hex"] = hex_color

            return {"is_online": True, "estado": estado}
        except Exception as e:
            return {"is_online": False, "error": str(e)}

    def _connected_device(self, device: dict, timeout: float = 3.0):
        dev = self._get_device(device, timeout=timeout)
        dev.set_socketPersistent(True)
        raw = dev.status()
        return dev, raw

    def encender(self, device: dict) -> dict:
        try:
            dev, _ = self._connected_device(device)
            dev.turn_on()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def apagar(self, device: dict) -> dict:
        try:
            dev, _ = self._connected_device(device)
            dev.turn_off()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def brillo(self, device: dict, valor: int) -> dict:
        if not self._is_bulb(device):
            return {"ok": False, "error": "Este dispositivo no soporta brillo"}
        valor_tuya = max(10, min(1000, int(valor * 10)))
        try:
            dev, raw = self._connected_device(device)
            if not raw or "Error" in raw:
                return {"ok": False, "error": "No se pudo conectar con la bombilla"}
            dev.set_value(22, valor_tuya)
            return {"ok": True, "brillo": valor}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def color_rgb(self, device: dict, r: int, g: int, b: int) -> dict:
        if not self._is_bulb(device):
            return {"ok": False, "error": "Este dispositivo no soporta color RGB"}
        try:
            dev, raw = self._connected_device(device)
            if not raw or "Error" in raw:
                return {"ok": False, "error": "No se pudo conectar con la bombilla"}
            dev.set_colour(r, g, b)
            return {"ok": True, "color": {"r": r, "g": g, "b": b}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def temperatura_color(self, device: dict, valor: int) -> dict:
        if not self._is_bulb(device):
            return {"ok": False, "error": "Este dispositivo no soporta temperatura de color"}
        try:
            dev, raw = self._connected_device(device)
            if not raw or "Error" in raw:
                return {"ok": False, "error": "No se pudo conectar con la bombilla"}
            # Convert Kelvin (2700-6500) to Tuya scale (0-1000)
            # Values <= 100 treated as percentage
            if valor <= 100:
                tuya_val = int(valor * 10)
            else:
                tuya_val = int((valor - 2700) / (6500 - 2700) * 1000)
            tuya_val = max(0, min(1000, tuya_val))
            dev.set_colourtemp(tuya_val)
            return {"ok": True, "temperatura": valor}
        except Exception as e:
            return {"ok": False, "error": str(e)}
