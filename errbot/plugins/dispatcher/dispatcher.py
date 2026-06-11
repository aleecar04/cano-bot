import json
import random
import uuid
from errbot import BotPlugin

from plugins._core import BasePlugin
from plugins._helpers import resolve_sender
from plugins.command_formatters import format_command_response
from plugins.dispatcher.handlers import handle_device_command
from api import is_backend_reachable
from api import commands as api_commands
from api import messages as api_messages


_NO_UNDERSTAND = [
    "No te he entendido, prueba de otra forma.",
    "Escríbelo de otra manera, por favor.",
    "No lo he pillado. Intenta de nuevo.",
]


_INTENT_TO_PLUGIN = {
    "saludo":   "who_are_you",
    "mi_ip":    "mi_ip",
    "ayuda":    "ayuda",
    "acciones": "acciones",
}


def _not_understand() -> str:
    return random.choice(_NO_UNDERSTAND)


def _split_correlation(text: str) -> tuple[str | None, str]:
    sep = text.find("|")
    if sep == -1:
        return None, text
    maybe_id = text[:sep]
    try:
        uuid.UUID(maybe_id)
    except ValueError:
        return None, text
    return maybe_id, text[sep + 1:].strip()


class Dispatcher(BasePlugin, BotPlugin):

    def callback_message(self, msg):
        text = msg.body.strip()
        if not text:
            return

        correlation_id, text = _split_correlation(text)
        msg.extras["correlation_id"] = correlation_id

        sender_id = self._check_sender_access(msg)
        if sender_id is None:
            return

        if self._handle_structured_message(text, msg):
            return

        intent_data, text = self._extract_natural_classified(text)
        if intent_data is None:
            self._forward_natural_to_backend(msg, text)
            return

        self._dispatch_intent(intent_data, msg, text, sender_id)

    def _check_sender_access(self, msg) -> str | None:
        try:
            sender_id = resolve_sender(str(msg.frm))
        except Exception:
            return ""
        if not sender_id:
            self.send(msg.frm, "No tienes acceso a este sistema. Pide al propietario un código de invitación.")
            return None
        return sender_id


    def _handle_structured_message(self, text: str, msg) -> bool:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return False

        if data.get("type") == "poll_device":
            method = self._get_command_from_plugins("poll_device")
            method(msg, data.get("device_id", ""))
            return True
        if data.get("type") == "scan":
            self._handle_scan_command(msg, data.get("command_id"))
            return True
        if data.get("type") == "relay":
            self._reply(msg, "", data.get("text", ""))
            return True
        if "device_id" in data and "action" in data:
            handle_device_command(data, msg, self)
            return True
        return False


    def _extract_natural_classified(self, text: str) -> tuple[dict | None, str]:
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None, text
        if data.get("type") != "natural_classified":
            return None, text
        return data.get("intent_data") or {}, data.get("original_body", "")


    def _forward_natural_to_backend(self, msg, text: str) -> None:
        if not is_backend_reachable():
            self.send(msg.frm, "El servicio no está disponible ahora mismo. Inténtalo más tarde.")
            return
        try:
            api_messages.forward_from_gajim(str(msg.frm), text)
        except Exception as e:
            self.log.error(f"Error reenviando mensaje Gajim al backend: {e}")
            self.send(msg.frm, "No he podido procesar tu mensaje. Inténtalo más tarde.")

    def _dispatch_intent(self, intent_data: dict, msg, text: str, sender_id: str) -> None:
        intent = intent_data.get("intent", "unknown")
        self.log.info(f"Intent: {intent} for '{text}'")

        if intent == "scan_devices":
            self._handle_chat_query(msg, text, action="scan_devices", command_name="scan_devices")
            return

        if intent == "list_devices":
            self._handle_chat_query(msg, text, action="list_devices", command_name="list_devices")
            return

        cmd_name = _INTENT_TO_PLUGIN.get(intent)
        if cmd_name and self._invoke_info_plugin(cmd_name, intent, intent_data, msg, text, sender_id):
            return

        self._reply(msg, text, _not_understand())

    def _invoke_info_plugin(self, cmd_name: str, intent: str, intent_data: dict,
                            msg, text: str, sender_id: str) -> bool:
        method = self._get_command_from_plugins(cmd_name)
        if not method:
            return False
        args = intent_data.get("device", "") if cmd_name == "acciones" else ""
        response = method(msg, args)
        self._reply(msg, text, response)
        self._register_command_in_backend(
            user_id=sender_id,
            device_id=None,
            action=intent,
            payload={},
            error=None,
            message_id=msg.extras.get("correlation_id"),
            result_data=None,
        )
        return True

    def _run_plugin(self, msg, command_name: str) -> dict:
        method = self._get_command_from_plugins(command_name)
        if not method:
            return {"tipo": "error", "mensaje": f"'{command_name}' no disponible"}
        return method(msg, "")

    def _handle_scan_command(self, msg, command_id) -> None:
        data = self._run_plugin(msg, "scan_devices")
        error = data.get("mensaje") if data.get("tipo") == "error" else None
        self._update_command_in_backend(command_id, error=error, result_data=None if error else data)

    def _handle_chat_query(self, msg, text: str, action: str, command_name: str) -> None:
        sender_id = resolve_sender(str(msg.frm))
        if not sender_id:
            return

        if not is_backend_reachable():
            # Sin backend no hay pending posible: ejecutamos y respondemos sin registrar.
            data = self._run_plugin(msg, command_name)
            error = data.get("mensaje") if data.get("tipo") == "error" else None
            self._reply(msg, text, format_command_response(action, data, "", ok=not error, error=error))
            return

        command_id = None
        try:
            cmd = api_commands.register_pending_from_bot(
                user_id=sender_id,
                device_id=None,
                action=action,
                payload={},
                message_id=msg.extras.get("correlation_id"),
            )
            command_id = cmd.get("command_id")
        except Exception as e:
            self.log.error(f"Error creating pending command for {action}: {e}")

        data = self._run_plugin(msg, command_name)
        error = data.get("mensaje") if data.get("tipo") == "error" else None

        self._reply(msg, text, format_command_response(action, data, "", ok=not error, error=error))

        if command_id:
            self._update_command_in_backend(
                command_id,
                error=error,
                result_data=None if error else data,
            )

    def _update_command_in_backend(self, command_id: str, error: str | None, result_data: dict | None = None) -> None:
        if not is_backend_reachable():
            return
        try:
            api_commands.patch_result(command_id, error, result_data)
        except Exception as e:
            self.log.error(f"Error updating command {command_id}: {e}")

    def _register_command_in_backend(
        self,
        user_id: str | None,
        device_id: str | None,
        action: str | None,
        payload: dict,
        error: str | None,
        message_id: str | None,
        result_data: dict | None = None,
    ) -> None:
        if not is_backend_reachable():
            return
        try:
            api_commands.register_from_bot(
                user_id=user_id,
                device_id=device_id,
                action=action,
                payload=payload,
                error=error,
                message_id=message_id,
                result_data=result_data,
            )
        except Exception as e:
            self.log.error(f"Error registering command in backend: {e}")

    def _get_command_from_plugins(self, command: str):
        return self._bot.all_commands.get(command)

    def _reply(self, msg, text: str, response: str) -> None:
        self.log_message(str(msg.frm), text, response, msg.extras.get("correlation_id"))
        self.send(msg.frm, response)
