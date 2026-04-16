import json
import requests  # used in _registrar_comando_en_backend
from errbot import BotPlugin

from plugins._core import BasePlugin, is_backend_reachable
from plugins._helpers import get_user_id_from_jid, buscar_dispositivo_por_nombre
from plugins._intent_classifier import classify_intent
from plugins.bot_config import BACKEND_URL, WEBHOOK_HEADERS

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

        try:
            data = json.loads(texto)
            if "device_id" in data and "accion" in data:
                self._handle_device_command(data, msg)
                return
        except (json.JSONDecodeError, TypeError):
            pass

        intent_data = classify_intent(texto)
        intent = intent_data.get("intent", "unknown")
        self.log.info(f"Intent: {intent} for '{texto}'")

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
        self._registrar_comando_en_backend(
            user_id=None,
            device_id=data.get("device_id"),
            accion=data.get("accion"),
            payload=data.get("payload", {}),
            error=resultado.get("error"),
            xmpp_message_id=getattr(msg, "id", None),
        )

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

            metodo = self._get_command_from_plugins("control_device")
            if not metodo:
                respuesta = "Error interno: control_device no disponible."
                self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
                self.send(msg.frm, respuesta)
                return

            args = json.dumps({
                "device_id": device["id"],
                "accion": accion,
                "payload": intent_data.get("payload", {}),
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
                payload=intent_data.get("payload", {}),
                error=resultado.get("error"),
                xmpp_message_id=getattr(msg, "id", None),
            )

        except Exception as e:
            self.log.error(f"Error in natural command: {e}")
            respuesta = "Ha ocurrido un error ejecutando el comando."
            self.log_message(str(msg.frm), texto, respuesta, getattr(msg, "id", None))
            self.send(msg.frm, respuesta)

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
