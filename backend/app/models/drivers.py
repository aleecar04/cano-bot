from enum import StrEnum


class DriverType(StrEnum):
    TUYA          = "tuya"
    LG_TV         = "lg_tv"
    HOMEASSISTANT = "homeassistant"
    GENERIC       = "generic"
