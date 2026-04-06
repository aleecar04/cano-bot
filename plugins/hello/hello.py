from errbot import BotPlugin, botcmd

from plugins._core import BasePlugin


class Hello(BasePlugin, BotPlugin):
    """Plugin de prueba del bot"""

    @botcmd
    def tryme(self, msg, args):
        """Comando de prueba básico"""
        return "It *works*!"
