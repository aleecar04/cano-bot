import json
from errbot import BotPlugin, botcmd
from plugins._core import BasePlugin
from scanner_service import get_local_network, scan_network


class Scanner(BasePlugin, BotPlugin):

    @botcmd
    def scan_devices(self, msg, args):
        """Escanea los dispositivos conectados a la red local
        Uso: scan_devices [red_cidr]
        """
        try:
            if args and args.strip():
                red = args.strip()
                ip_local = None
            else:
                ip_local, red = get_local_network()
                if not red:
                    return json.dumps({"tipo": "error", "mensaje": "No se pudo detectar la red local"})

            dispositivos = scan_network(red)
            self.log.info(f"Dispositivos encontrados: {len(dispositivos)}")

            return json.dumps({
                "tipo": "scan_response",
                "red": red,
                "ip_bot": ip_local,
                "dispositivos": dispositivos,
                "total": len(dispositivos)
            })
        except Exception as e:
            self.log.error(f"Error en scan_devices: {e}", exc_info=True)
            return json.dumps({"tipo": "error", "mensaje": str(e)})