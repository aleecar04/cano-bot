import re

from errbot import BotPlugin
import random
import os
from dotenv import load_dotenv

load_dotenv()

from plugins._core import BasePlugin
from plugins._intent_classifier import classify_intent

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class Dispatcher(BasePlugin, BotPlugin):
    """Plugin dispatcher para gestionar mensajes y rutas de comandos"""

    def not_understand(self, msg, args):
        respuestas = [
            "Ey tío, mejora esa ortografía que no te entiendo",
            "Esa boca PECADOOOR, escribe bien",
            "No te entiendo, por favor escríbemelo otra vez"
        ]
        return random.choice(respuestas)

    def callback_message(self, msg):
        texto = msg.body.strip()
        if not texto:
            return

        # Si ya lo maneja un @re_botcmd, no procesar
        for pattern in self._bot.re_commands:
            if re.search(pattern, texto):
                return

        intent = classify_intent(texto)
        self.log.info(f"Intent detectado: {intent} para '{texto}'")

        intent_map = {
            "scan_devices": "scan_devices",
            "mi_ip":        "mi_ip",
            "saludo":       "who_are_you",
        }

        cmd_name = intent_map.get(intent)
        if cmd_name:
            metodo = self._get_command_from_plugins(cmd_name)
            if metodo:
                respuesta = metodo(msg, '')
                self.log_message(str(msg.frm), texto, respuesta)
                self.send(msg.frm, respuesta)
                return

        respuesta = self.not_understand(msg, '')
        self.log_message(str(msg.frm), texto, respuesta)
        self.send(msg.frm, respuesta)

    def _get_command_from_plugins(self, comando):
        all_commands = self._bot.all_commands if hasattr(self._bot, 'all_commands') else {}
        return all_commands.get(comando, None)