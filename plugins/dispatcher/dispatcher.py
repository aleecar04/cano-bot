import json
import re
import requests  # used in _registrar_comando_en_backend
from errbot import BotPlugin

from plugins._core import BasePlugin, is_backend_reachable
from plugins._helpers import get_user_id_from_jid, buscar_dispositivo_por_nombre, is_house_member
from plugins._intent_classifier import classify_intent
from plugins.bot_config import BACKEND_URL, WEBHOOK_HEADERS

_ACCIONES_CON_VALOR = {"brillo", "temperatura_color", "set_volumen"}

_ACCIONES_DESCRIPCION: dict[str, str] = {
    "encender":          "encender",
    "apagar":            "apagar",
    "brillo":            "brillo  (valor: 0-100)",
    "temperatura_color": "temperatura_color  (cálida=2700K · neutra=4000K · fría=6500K)",
    "color_rgb":         "color_rgb  (rojo, naranja, amarillo, verde, cyan, azul, morado, violeta, rosa, blanco)",
    "subir_volumen":     "subir_volumen",
    "bajar_volumen":     "bajar_volumen",
    "mute":              "mute",
    "set_volumen":       "set_volumen  (valor: 0-100)",
    "abrir_app":         "abrir_app  (netflix, youtube, prime, disney)",
}

_TIPO_LABEL: dict[str, str] = {
    "Luz":          "Luz / Bombilla",
    "SmartTV":      "Smart TV",
    "Altavoz":      "Altavoz",
    "Enchufe":      "Enchufe",
    "Persiana":     "Persiana",
    "Termostato":   "Termostato",
    "IoT":          "IoT",
    "Ordenador":    "Ordenador",
    "light":        "Luz (HA)",
    "switch":       "Switch (HA)",
    "media_player": "Media Player (HA)",
    "cover":        "Persiana (HA)",
    "climate":      "Clima (HA)",
}

_TIPOS_GENERICOS = ["Luz", "SmartTV", "Altavoz", "Enchufe", "Persiana", "Termostato", "IoT", "Ordenador"]

_AYUDA_TEXT = (
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

_TEMP_PRESETS: dict[int, str] = {2700: "Cálida", 4000: "Neutra", 6500: "Fría"}
_COLOR_NAMES: frozenset[str] = frozenset({
    "rojo", "naranja", "amarillo", "verde", "cyan",
    "azul", "morado", "violeta", "rosa", "blanco",
})


def _validate_action_payload(accion: str, payload: dict) -> str | None:
    if accion == "temperatura_color":
        valor = payload.get("valor")
        if valor is None or int(valor) not in _TEMP_PRESETS:
            return (
                "Solo acepto estas temperaturas de color:\n"
                "  • Cálida → 2700K\n"
                "  • Neutra → 4000K\n"
                "  • Fría → 6500K\n"
                "Prueba: \"luz cálida\", \"temperatura neutra\" o \"luz fría\"."
            )
    elif accion == "color_rgb":
        color = str(payload.get("color", "")).lower()
        if color not in _COLOR_NAMES:
            return (
                "Lo siento, ese color no está dentro de los colores soportados. "
                "Prueba con alguno de los siguientes:\n"
                "rojo, naranja, amarillo, verde, cyan, azul, morado, violeta, rosa, blanco."
            )
    return None

# Acciones soportadas por tipo de dispositivo (None = sin restricción)
_ACCIONES_POR_TIPO: dict[str, set[str]] = {
    "Luz":          {"encender", "apagar", "brillo", "temperatura_color", "color_rgb"},
    "light":        {"encender", "apagar", "brillo", "temperatura_color"},
    "SmartTV":      {"encender", "apagar", "subir_volumen", "bajar_volumen", "mute", "set_volumen", "abrir_app"},
    "media_player": {"encender", "apagar", "subir_volumen", "bajar_volumen", "mute", "set_volumen"},
    "Altavoz":      {"encender", "apagar", "subir_volumen", "bajar_volumen", "mute"},
    "Enchufe":      {"encender", "apagar"},
    "Persiana":     {"encender", "apagar"},   # encender = abrir, apagar = cerrar
    "Sensor":       set(),                    # read-only, no control actions
    "sensor":       set(),
    "Termostato":   {"encender", "apagar"},
    "IoT":          {"encender", "apagar"},
    "switch":       {"encender", "apagar"},
    "climate":      {"encender", "apagar"},
    "cover":        {"encender", "apagar"},
    "Ordenador":    {"encender", "apagar"},
}

def _accion_soportada(device: dict, accion: str) -> bool:
    tipo = device.get("type", "")
    soportadas = _ACCIONES_POR_TIPO.get(tipo)
    if soportadas is None:
        return True  # tipo desconocido: permitir todo
    return accion in soportadas


def _extraer_valor(texto: str) -> int | None:
    match = re.search(r'\b(\d+)\b', texto)
    return int(match.group(1)) if match else None

_NO_UNDERSTAND = [
    "No te he entendido, prueba de otra forma.",
    "Escríbelo de otra manera, por favor.",
    "No lo he pillado. Intenta de nuevo.",
]
_no_understand_idx = 0


def _not_understand() -> str:
    global _no_understand_idx
    msg = _NO_UNDERSTAND[_no_understand_idx % len(_NO_UNDERSTAND)]
    _no_understand_idx += 1
    return msg


class Dispatcher(BasePlugin, BotPlugin):

    def callback_message(self, msg):
        texto = msg.body.strip()
        if not texto or texto.startswith("!"):
            return

        # Verify sender belongs to this bot's house
        try:
            sender_user_id = get_user_id_from_jid(str(msg.frm))
            if not is_house_member(sender_user_id):
                self.send(msg.frm, "No tienes acceso a este sistema. Pide al propietario un código de invitación.")
                return
        except Exception:
            pass  # If JID unknown or backend down, let it through

        try:
            data = json.loads(texto)
            if data.get("type") == "poll_device":
                metodo = self._get_command_from_plugins("poll_device")
                if metodo:
                    metodo(msg, data.get("device_id", ""))
                return
            if "device_id" in data and "accion" in data:
                self._handle_device_command(data, msg)
                return
        except (json.JSONDecodeError, TypeError):
            pass

        texto_lower = texto.lower()
        if any(kw in texto_lower for kw in ("ayuda", "help", "ayúdame", "qué puedes hacer", "que puedes hacer")):
            self._handle_ayuda(msg, texto)
            return
        if any(kw in texto_lower for kw in ("acciones", "qué soporta", "que soporta")):
            self._handle_acciones(msg, texto)
            return
        if any(kw in texto_lower for kw in ("escanear", "escanea", "scan", "buscar dispositivos", "buscar en la red")):
            metodo = self._get_command_from_plugins("scan_devices")
            if metodo:
                respuesta = metodo(msg, "")
                self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
                self.send(msg.frm, respuesta)
            return

        intent_data = classify_intent(texto)
        intent = intent_data.get("intent", "unknown")
        self.log.info(f"Intent: {intent} for '{texto}'")

        if intent == "ollama_error":
            respuesta = "Estoy teniendo problemas para clasificar tu mensaje, inténtalo de nuevo en breves."
            self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
            self.send(msg.frm, respuesta)
            return

        if intent == "control_device":
            self._handle_natural_device_command(intent_data, msg, texto)
            return

        intent_map = {
            "scan_devices": "scan_devices",
            "saludo": "who_are_you",
            "list_devices": "list_devices",
            "mi_ip": "mi_ip",
        }
        cmd_name = intent_map.get(intent)
        if cmd_name:
            metodo = self._get_command_from_plugins(cmd_name)
            if metodo:
                respuesta = metodo(msg, "")
                self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
                self.send(msg.frm, respuesta)
                return

        respuesta = _not_understand()
        self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
        self.send(msg.frm, respuesta)

    def _handle_device_command(self, data: dict, msg):
        command_id = data.get("command_id")
        metodo = self._get_command_from_plugins("control_device")
        if not metodo:
            self.send(msg.frm, "Internal error: control_device not available")
            return
        resultado = json.loads(metodo(msg, json.dumps(data)))
        if resultado.get("ok"):
            respuesta = "Command executed"
        else:
            respuesta = f"Error: {resultado.get('error', 'unknown')}"
        self.send(msg.frm, respuesta)
        if command_id:
            self._actualizar_comando_en_backend(command_id, error=resultado.get("error"))

    def _handle_natural_device_command(self, intent_data: dict, msg, texto: str):
        accion = intent_data.get("accion")
        nombre = intent_data.get("dispositivo", "").lower()

        if not accion or not nombre:
            respuesta = "No he entendido qué dispositivo quieres controlar."
            self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
            self.send(msg.frm, respuesta)
            return

        try:
            user_id = get_user_id_from_jid(str(msg.frm))
            device = buscar_dispositivo_por_nombre(nombre, user_id)

            if not device:
                respuesta = f"No he encontrado ningún dispositivo llamado '{nombre}'."
                self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
                self.send(msg.frm, respuesta)
                return

            if not _accion_soportada(device, accion):
                respuesta = f"{device['name']} no soporta la acción '{accion}'."
                self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
                self.send(msg.frm, respuesta)
                return

            metodo = self._get_command_from_plugins("control_device")
            if not metodo:
                respuesta = "Error interno: control_device no disponible."
                self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
                self.send(msg.frm, respuesta)
                return

            payload = intent_data.get("payload", {})
            if accion in _ACCIONES_CON_VALOR and "valor" not in payload:
                valor = _extraer_valor(texto)
                if valor is not None:
                    payload = {"valor": valor}
                    self.log.info(f"Valor extraído por regex: {valor} para acción '{accion}'")

            error_payload = _validate_action_payload(accion, payload)
            if error_payload:
                self.log_message(str(msg.frm), texto, error_payload, getattr(msg, "id", None))
                self.send(msg.frm, error_payload)
                return

            args = json.dumps({
                "device_id": device["id"],
                "accion": accion,
                "payload": payload,
            })
            resultado = json.loads(metodo(msg, args))

            if resultado.get("ok"):
                respuesta = f"{device['name']}: {accion} ejecutado."
            else:
                respuesta = f"Error: {resultado.get('error', 'desconocido')}."

            self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
            self.send(msg.frm, respuesta)

            self._registrar_comando_en_backend(
                user_id=user_id,
                device_id=device["id"],
                accion=accion,
                payload=payload,
                error=resultado.get("error"),
                xmpp_message_id=getattr(msg, "id", None),
            )

        except Exception as e:
            self.log.error(f"Error in natural command: {e}")
            respuesta = "Ha ocurrido un error ejecutando el comando."
            self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
            self.send(msg.frm, respuesta)

    def _actualizar_comando_en_backend(self, command_id: str, error: str | None) -> None:
        if not is_backend_reachable():
            return
        try:
            requests.patch(
                f"{BACKEND_URL}/api/v1/commands/{command_id}",
                json={"error": error},
                headers=WEBHOOK_HEADERS,
                timeout=3,
            )
        except Exception as e:
            self.log.error(f"Error updating command {command_id}: {e}")

    def _registrar_comando_en_backend(
        self,
        user_id: str | None,
        device_id: str | None,
        accion: str | None,
        payload: dict,
        error: str | None,
        xmpp_message_id: str | None,
    ) -> None:
        if not is_backend_reachable():
            return
        try:
            requests.post(
                f"{BACKEND_URL}/api/v1/commands/from-bot",
                json={
                    "user_id": user_id,
                    "device_id": device_id,
                    "action": accion,
                    "payload": payload,
                    "error": error,
                    "xmpp_message_id": xmpp_message_id,
                },
                headers=WEBHOOK_HEADERS,
                timeout=3,
            )
        except Exception as e:
            self.log.error(f"Error registering command in backend: {e}")

    def _get_command_from_plugins(self, comando: str):
        all_commands = self._bot.all_commands if hasattr(self._bot, "all_commands") else {}
        return all_commands.get(comando)

    def _handle_ayuda(self, msg, texto: str):
        self.log_message(str(msg.frm), texto, _AYUDA_TEXT, getattr(msg, "id", None))
        self.send(msg.frm, _AYUDA_TEXT)

    def _handle_acciones(self, msg, texto: str):
        m = re.search(
            r'(?:acciones\s+de(?:\s+(?:la|el|los|las|un|una))?\s+|soporta\s+(?:la|el|los|las|un|una)?\s*)(.+)',
            texto.lower(),
        )
        nombre = m.group(1).strip() if m else None

        if nombre:
            try:
                user_id = get_user_id_from_jid(str(msg.frm))
                device  = buscar_dispositivo_por_nombre(nombre, user_id)
            except Exception:
                device = None

            if not device:
                respuesta = f"No he encontrado ningún dispositivo llamado '{nombre}'."
            else:
                tipo   = device.get("type", "")
                label  = _TIPO_LABEL.get(tipo, tipo)
                acts   = set(_ACCIONES_POR_TIPO.get(tipo, set()))
                if tipo == "Luz" and device.get("driver") == "tuya":
                    acts.add("color_rgb")
                lines = [f"{device['name']} ({label}):"]
                for a in sorted(acts):
                    lines.append(f"  • {_ACCIONES_DESCRIPCION.get(a, a)}")
                respuesta = "\n".join(lines)
        else:
            lines = ["Acciones por tipo de dispositivo:\n"]
            for tipo in _TIPOS_GENERICOS:
                acts = _ACCIONES_POR_TIPO.get(tipo)
                if not acts:
                    continue
                lines.append(f"{_TIPO_LABEL.get(tipo, tipo)}:")
                for a in sorted(acts):
                    lines.append(f"  • {_ACCIONES_DESCRIPCION.get(a, a)}")
                if tipo == "Luz":
                    lines.append(f"  • {_ACCIONES_DESCRIPCION['color_rgb']}  [solo Tuya]")
                lines.append("")
            respuesta = "\n".join(lines).strip()

        self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
        self.send(msg.frm, respuesta)
