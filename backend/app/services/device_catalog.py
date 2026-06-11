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


_ACTIONS_BY_CATEGORY: dict[str, set[Action]] = {
    "Luz":     {Action.ENCENDER, Action.APAGAR, Action.BRILLO, Action.TEMPERATURA_COLOR, Action.COLOR_RGB},
    "Enchufe": {Action.ENCENDER, Action.APAGAR},
    "SmartTV": {Action.ENCENDER, Action.APAGAR, Action.SUBIR_VOLUMEN, Action.BAJAR_VOLUMEN, Action.MUTE, Action.SET_VOLUMEN, Action.ABRIR_APP},
    "Altavoz": {Action.ENCENDER, Action.APAGAR, Action.SUBIR_VOLUMEN, Action.BAJAR_VOLUMEN, Action.MUTE},
    "Clima":   {Action.ENCENDER, Action.APAGAR},
}

_TYPE_TO_CATEGORY: dict[str, str] = {
    "Luz":          "Luz",
    "Enchufe":      "Enchufe",
    "SmartTV":      "SmartTV",
    "Altavoz":      "Altavoz",
    "IoT":          "Enchufe",
    "light":        "Luz",
    "switch":       "Enchufe",
    "media_player": "SmartTV",
    "climate":      "Clima",
}

_TEMPERATURE_PRESETS: frozenset[int] = frozenset({2700, 4000, 6500})
_COLOR_NAMES: frozenset[str] = frozenset({
    "rojo", "naranja", "amarillo", "verde", "cyan",
    "azul", "morado", "violeta", "rosa", "blanco",
})


def is_action_supported(device_type: str, action: str) -> bool:
    """True si el tipo de dispositivo soporta la acción."""
    category = _TYPE_TO_CATEGORY.get(device_type)
    if category is None:
        return False
    try:
        return Action(action) in _ACTIONS_BY_CATEGORY[category]
    except ValueError:
        return False


def validate_payload(action: str, payload: dict) -> str | None:
    """Devuelve mensaje de error humano si el payload es inválido, o None si OK."""
    if action == Action.TEMPERATURA_COLOR.value:
        value = payload.get("value")
        if value is None or int(value) not in _TEMPERATURE_PRESETS:
            return (
                "Solo acepto estas temperaturas de color:\n"
                "  • Cálida → 2700K\n"
                "  • Neutra → 4000K\n"
                "  • Fría → 6500K"
            )
    elif action == Action.COLOR_RGB.value:
        color = str(payload.get("color", "")).lower()
        if color not in _COLOR_NAMES:
            return (
                "Ese color no está soportado. Prueba con alguno de:\n"
                + ", ".join(sorted(_COLOR_NAMES))
            )
    elif action in (Action.BRILLO.value, Action.SET_VOLUMEN.value):
        value = payload.get("value")
        try:
            v = int(value)
        except (TypeError, ValueError):
            return "El valor debe ser un número entre 0 y 100."
        if not 0 <= v <= 100:
            return "El valor debe estar entre 0 y 100."
    return None
