from errbot import BotPlugin, botcmd

from plugins._core import BasePlugin
from plugins._helpers import find_device_by_name
from drivers.actions_catalog import Action


HELP_TEXT = (
    "¡Hola! Soy Cano-bot. Esto es lo que puedo hacer:\n\n"
    "Dispositivos:\n"
    "  • \"enciende la luz\" / \"apaga la tele\"\n"
    "  • \"lista mis dispositivos\"\n"
    "  • \"escanea la red\"\n\n"
    "Luz / Bombilla:\n"
    "  • \"brillo al 75\"\n"
    "  • \"luz cálida\" / \"luz neutra\" / \"luz fría\"\n"
    "  • \"pon la luz en rojo\" / \"luz azul\" / \"luz verde\"...\n\n"
    "Smart TV:\n"
    "  • \"sube el volumen\" / \"volumen a 50\" / \"silencia la tele\"\n"
    "  • \"abre Netflix en la tele\"\n\n"
    "Ayuda:\n"
    "  • \"acciones\" → ver todas las acciones por tipo\n"
    "  • \"acciones de [nombre]\" → ver acciones de un dispositivo concreto"
)


ACTIONS_BY_CATEGORY: dict[str, set[Action]] = {
    "Luz":     {Action.ENCENDER, Action.APAGAR, Action.BRILLO, Action.TEMPERATURA_COLOR, Action.COLOR_RGB},
    "Enchufe": {Action.ENCENDER, Action.APAGAR},
    "SmartTV": {Action.ENCENDER, Action.APAGAR, Action.SUBIR_VOLUMEN, Action.BAJAR_VOLUMEN, Action.MUTE, Action.SET_VOLUMEN, Action.ABRIR_APP},
    "Altavoz": {Action.ENCENDER, Action.APAGAR, Action.SUBIR_VOLUMEN, Action.BAJAR_VOLUMEN, Action.MUTE},
    "Clima":   {Action.ENCENDER, Action.APAGAR},
}


CATEGORY_LABEL: dict[str, str] = {
    "Luz":     "Luz / Bombilla",
    "Enchufe": "Enchufe / Interruptor",
    "SmartTV": "Smart TV",
    "Altavoz": "Altavoz",
    "Clima":   "Aire acondicionado",
}

TYPE_TO_CATEGORY: dict[str, str] = {
    "Luz":          "Luz",
    "Enchufe":      "Enchufe",
    "SmartTV":      "SmartTV",
    "Altavoz":      "Altavoz",
    "IoT":          "Enchufe",
    # Tipos de Home Assistant
    "light":        "Luz",
    "switch":       "Enchufe",
    "media_player": "SmartTV",
    "climate":      "Clima",
}


ACTION_DESCRIPTIONS: dict[Action, str] = {
    Action.ENCENDER:          "encender",
    Action.APAGAR:            "apagar",
    Action.BRILLO:            "brillo  (valor: 0-100)",
    Action.TEMPERATURA_COLOR: "temperatura_color  (cálida=2700K · neutra=4000K · fría=6500K)",
    Action.COLOR_RGB:         "color_rgb  (rojo, naranja, amarillo, verde, cyan, azul, morado, violeta, rosa, blanco)",
    Action.SUBIR_VOLUMEN:     "subir_volumen",
    Action.BAJAR_VOLUMEN:     "bajar_volumen",
    Action.MUTE:              "mute",
    Action.SET_VOLUMEN:       "set_volumen  (valor: 0-100)",
    Action.ABRIR_APP:         "abrir_app  (netflix, youtube, prime)",
}


def get_supported_actions(internal_type: str) -> set[Action]:
    category = TYPE_TO_CATEGORY.get(internal_type)
    if category is None:
        return set()
    return ACTIONS_BY_CATEGORY[category]


def _format_actions_for_device(device: dict) -> str:
    internal_type = device.get("type", "")
    category      = TYPE_TO_CATEGORY.get(internal_type, internal_type)
    label         = CATEGORY_LABEL.get(category, category)
    actions       = get_supported_actions(internal_type)

    lines = [f"{device['name']} ({label}):"]
    for action in sorted(actions):
        lines.append(f"  • {ACTION_DESCRIPTIONS.get(action, action)}")
    return "\n".join(lines)


def _format_actions_by_category() -> str:
    lines = ["Acciones por tipo de dispositivo:\n"]
    for category, actions in ACTIONS_BY_CATEGORY.items():
        lines.append(f"{CATEGORY_LABEL[category]}:")
        for action in sorted(actions):
            lines.append(f"  • {ACTION_DESCRIPTIONS.get(action, action)}")
        lines.append("")
    return "\n".join(lines).strip()


def actions_list_data(name: str) -> dict | None:
    name = (name or "").strip().lower()
    if not name:
        grupos = [
            {
                "label": CATEGORY_LABEL[category],
                "acciones": [{"action": str(a), "desc": ACTION_DESCRIPTIONS.get(a, str(a))}
                             for a in sorted(actions)],
            }
            for category, actions in ACTIONS_BY_CATEGORY.items()
        ]
        return {"tipo": "actions_list", "grupos": grupos}

    device = find_device_by_name(name)
    if not device:
        return None
    internal_type = device.get("type", "")
    category = TYPE_TO_CATEGORY.get(internal_type, internal_type)
    return {
        "tipo": "actions_list",
        "device": device["name"],
        "device_type": internal_type,
        "label": CATEGORY_LABEL.get(category, category),
        "acciones": [{"action": str(a), "desc": ACTION_DESCRIPTIONS.get(a, str(a))}
                     for a in sorted(get_supported_actions(internal_type))],
    }


def help_data() -> dict:
    """Versión estructurada de la ayuda para renderizar en cajitas en la app."""
    return {
        "tipo": "help",
        "secciones": [
            {"titulo": "Dispositivos", "items": [
                "\"enciende la luz\" / \"apaga la tele\"",
                "\"lista mis dispositivos\"",
                "\"escanea la red\"",
            ]},
            {"titulo": "Luz / Bombilla", "items": [
                "\"brillo al 75\"",
                "\"luz cálida\" / \"luz neutra\" / \"luz fría\"",
                "\"pon la luz en rojo\" / \"luz azul\" / \"luz verde\"",
            ]},
            {"titulo": "Smart TV", "items": [
                "\"sube el volumen\" / \"volumen a 50\" / \"silencia la tele\"",
                "\"abre Netflix en la tele\"",
            ]},
            {"titulo": "Acciones", "items": [
                "\"acciones\" → todas por tipo",
                "\"acciones de [nombre]\" → de un dispositivo",
            ]},
        ],
    }


class Help(BasePlugin, BotPlugin):

    @botcmd
    def ayuda(self, msg, args):
        return HELP_TEXT

    @botcmd
    def acciones(self, msg, args):
        name = (args or "").strip().lower()
        if not name:
            return _format_actions_by_category()

        device = find_device_by_name(name)
        if not device:
            return f"No he encontrado ningún dispositivo llamado '{name}'."
        return _format_actions_for_device(device)
