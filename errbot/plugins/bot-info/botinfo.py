from errbot import BotPlugin, botcmd, re_botcmd
import subprocess

import requests

from plugins._core import BasePlugin


class BotInfo(BasePlugin, BotPlugin):

    @re_botcmd(pattern=r'(?i)(hola|buenos días|buenos dias|que tal|saludos|hallo|hey|buenos).*', prefixed=True)
    def who_are_you(self, msg, match):
        return "Hola, soy Cano-bot, tu asistente personal. Estoy aquí para ayudarte con la gestión de tu casa y aparatos domésticos."

    
    @botcmd
    def mi_ip(self, msg, args):
        try:
            ip = requests.get('https://ifconfig.me', timeout=5).text.strip()
            return f"Tu IP pública es: {ip}"
        except Exception as e:
            return f"Error obteniendo IP: {str(e)}"
