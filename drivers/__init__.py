from .ha_driver import HomeAssistantDriver
from .shelly_driver import ShellyDriver
from .tuya_driver import TuyaDriver
from .lg_tv import LGTVDriver
from .android_tv import AndroidTVDriver
from .samsung_tv import SamsungTVDriver

DRIVERS = {
    "tuya":          TuyaDriver(),
    "lg_tv":         LGTVDriver(),
    "android_tv":    AndroidTVDriver(),
    "samsung_tv":    SamsungTVDriver(),
    "homeassistant": HomeAssistantDriver(),
    "shelly":        ShellyDriver(),
}
def ejecutar_comando(device: dict, accion: str, payload: dict = None) -> dict:
    tipo   = device.get("driver")
    driver = DRIVERS.get(tipo)
    if not driver:
        return {"ok": False, "error": f"Driver '{tipo}' no reconocido"}
    return driver.ejecutar(device, accion, payload or {})