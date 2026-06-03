from enum import StrEnum

from .ha_driver import HomeAssistantDriver
from .tuya_driver import TuyaDriver
from .lg_tv import LGTVDriver
from .samsung_tv import SamsungTVDriver


class DriverType(StrEnum):
    TUYA          = "tuya"
    LG_TV         = "lg_tv"
    SAMSUNG_TV    = "samsung_tv"
    HOMEASSISTANT = "homeassistant"
    GENERIC       = "generic"


DRIVERS = {
    DriverType.TUYA:          TuyaDriver(),
    DriverType.LG_TV:         LGTVDriver(),
    DriverType.SAMSUNG_TV:    SamsungTVDriver(),
    DriverType.HOMEASSISTANT: HomeAssistantDriver(),
}
def ejecutar_comando(device: dict, accion: str, payload: dict = None) -> dict:
    tipo   = device.get("driver")
    driver = DRIVERS.get(tipo)
    if not driver:
        return {"ok": False, "error": f"Driver '{tipo}' no reconocido"}
    return driver.ejecutar(device, accion, payload or {})