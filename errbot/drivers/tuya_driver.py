import colorsys
import tinytuya
from dataclasses import dataclass
from .base import BaseDriver

_BULB_TYPES       = frozenset({"Luz", "light"})
_SENSOR_TYPES     = frozenset({"Sensor", "sensor"})
_WRITE_TIMEOUT_S  = 3.0   # más holgado que la lectura porque la bombilla puede tardar en responder
_BULB_UNREACHABLE = "No se pudo conectar con la bombilla"


@dataclass(frozen=True)
class TuyaConfig:
    dev_id:    str
    local_key: str
    version:   float = 3.4

    def __post_init__(self):
        if not self.dev_id or not self.local_key:
            raise ValueError("Tuya config requiere dev_id y local_key")

    @classmethod
    def from_dict(cls, data: dict) -> "TuyaConfig":
        return cls(
            dev_id=data.get("dev_id", ""),
            local_key=data.get("local_key", ""),
            version=float(data.get("version", 3.4)),
        )


def _tuya_hsv_to_hex(hsv_str: str) -> str | None:
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

    def _is_sensor(self, device: dict) -> bool:
        return device.get("type", "") in _SENSOR_TYPES

    def _get_device(self, device: dict, timeout: float = 2.0, persistent: bool = False):
        cfg = TuyaConfig.from_dict(device["config"])
        kwargs = {
            "dev_id":    cfg.dev_id,
            "address":   device["ip"],
            "local_key": cfg.local_key,
            "version":   cfg.version,
        }
        dev = tinytuya.BulbDevice(**kwargs) if self._is_bulb(device) else tinytuya.Device(**kwargs)
        dev.set_socketTimeout(timeout)
        if persistent:
            dev.set_socketPersistent(True)
        return dev

    def get_status(self, device: dict, timeout: float = 2.0) -> dict:
        try:
            dev = self._get_device(device, timeout=timeout)
            raw = dev.status()
            if not raw or "Error" in raw:
                return {"is_online": False, "error": raw.get("Error") if raw else "no response"}
            dps = raw.get("dps", {})
            estado = (self._parse_sensor_estado(dps) if self._is_sensor(device)
                      else self._parse_bulb_switch_estado(device, dps))
            return {"is_online": True, "estado": estado}
        except Exception as e:
            return {"is_online": False, "error": str(e)}

    def _parse_sensor_estado(self, dps: dict) -> dict:
        """DPS habituales: 1=temp (×0.1°C), 2=humedad, 4=batería. Algunos modelos usan 101/102/104."""
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
        return estado

    def _parse_bulb_switch_estado(self, device: dict, dps: dict) -> dict:
        """Bombillas usan DPS 20 para power; enchufes/switches usan DPS 1.
        En bombillas se leen además work_mode (21), brillo (22), temp color (23) y color HSV (24)."""
        power_dps = "20" if self._is_bulb(device) else "1"
        estado: dict = {"power": "on" if dps.get(power_dps, False) else "off"}
        if not self._is_bulb(device):
            return estado
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
        return estado

    def _with_device(self, device: dict, on_ready) -> dict:
        """Abre la conexión, comprueba que la bombilla responde y ejecuta `on_ready(dev)`.
        Si el device no contesta o tinytuya devuelve un dict con 'Error',
        cortocircuita con un mensaje humano sin intentar la acción."""
        try:
            dev = self._get_device(device, timeout=_WRITE_TIMEOUT_S, persistent=True)
            raw = dev.status()
            if not raw or "Error" in raw:
                return {"ok": False, "error": _BULB_UNREACHABLE}
            return on_ready(dev)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def encender(self, device: dict) -> dict:
        def _do(dev):
            dev.turn_on()
            return {"ok": True}
        return self._with_device(device, _do)

    def apagar(self, device: dict) -> dict:
        def _do(dev):
            dev.turn_off()
            return {"ok": True}
        return self._with_device(device, _do)

    def brillo(self, device: dict, valor: int) -> dict:
        if not self._is_bulb(device):
            return {"ok": False, "error": "Este dispositivo no soporta brillo"}
        valor_tuya = max(10, min(1000, int(valor * 10)))
        def _do(dev):
            dev.set_value(22, valor_tuya)
            return {"ok": True, "brillo": valor}
        return self._with_device(device, _do)

    def color_rgb(self, device: dict, r: int, g: int, b: int) -> dict:
        if not self._is_bulb(device):
            return {"ok": False, "error": "Este dispositivo no soporta color RGB"}
        def _do(dev):
            dev.set_colour(r, g, b)
            return {"ok": True, "color": {"r": r, "g": g, "b": b}}
        return self._with_device(device, _do)

    def temperatura_color(self, device: dict, valor: int) -> dict:
        if not self._is_bulb(device):
            return {"ok": False, "error": "Este dispositivo no soporta temperatura de color"}
        # Convert Kelvin (2700-6500) to Tuya scale (0-1000).
        # Valores <= 100 se tratan como porcentaje (legado).
        if valor <= 100:
            tuya_val = int(valor * 10)
        else:
            tuya_val = int((valor - 2700) / (6500 - 2700) * 1000)
        tuya_val = max(0, min(1000, tuya_val))
        def _do(dev):
            dev.set_colourtemp(tuya_val)
            return {"ok": True, "temperatura": valor}
        return self._with_device(device, _do)
