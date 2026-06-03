from enum import StrEnum


class DriverType(StrEnum):
    """Tipos de driver soportados por el bot. Espejo del enum definido en errbot/drivers/__init__.py
    para evitar que el backend dependa del paquete del bot."""
    TUYA          = "tuya"
    LG_TV         = "lg_tv"
    SAMSUNG_TV    = "samsung_tv"
    HOMEASSISTANT = "homeassistant"
    GENERIC       = "generic"
