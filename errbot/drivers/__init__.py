from enum import StrEnum

from .ha_driver import HomeAssistantDriver
from .tuya_driver import TuyaDriver
from .lg_tv import LGTVDriver


class DriverType(StrEnum):
    TUYA          = "tuya"
    LG_TV         = "lg_tv"
    HOMEASSISTANT = "homeassistant"
    GENERIC       = "generic"


DRIVERS = {
    DriverType.TUYA:          TuyaDriver(),
    DriverType.LG_TV:         LGTVDriver(),
    DriverType.HOMEASSISTANT: HomeAssistantDriver(),
}


def execute_command(device: dict, action: str, payload: dict = None) -> dict:
    driver_type = device.get("driver")
    driver = DRIVERS.get(driver_type)
    if not driver:
        return {"ok": False, "error": f"Driver '{driver_type}' no reconocido"}
    return driver.execute(device, action, payload or {})
