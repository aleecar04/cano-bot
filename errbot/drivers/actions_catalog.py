from enum import StrEnum


class Action(StrEnum):
    ENCENDER          = "encender"
    APAGAR            = "apagar"
    BRILLO            = "brillo"
    TEMPERATURA_COLOR = "temperatura_color"
    COLOR_RGB         = "color_rgb"
    SUBIR_VOLUMEN     = "subir_volumen"
    BAJAR_VOLUMEN     = "bajar_volumen"
    MUTE              = "mute"
    SET_VOLUMEN       = "set_volumen"
    ABRIR_APP         = "abrir_app"