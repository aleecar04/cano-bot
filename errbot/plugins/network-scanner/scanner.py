from dataclasses import asdict
from errbot import BotPlugin, botcmd
from plugins._core import BasePlugin
from scanner_service import get_local_network, scan_network


class Scanner(BasePlugin, BotPlugin):

    @botcmd
    def scan_devices(self, msg, args):
        """Escanea la red local y devuelve el resultado estructurado (dict),
        que el dispatcher guarda en command.result_data."""
        try:
            if args and args.strip():
                red = args.strip()
                ip_local = None
            else:
                ip_local, red = get_local_network()
                if not red:
                    return {"tipo": "error", "mensaje": "No se pudo detectar la red local"}

            dispositivos = scan_network(red)
            self.log.info(f"Dispositivos encontrados: {len(dispositivos)}")

            return {
                "tipo": "scan_response",
                "red": red,
                "ip_bot": ip_local,
                "dispositivos": [asdict(d) for d in dispositivos],
                "total": len(dispositivos),
            }
        except Exception as e:
            self.log.error(f"Error en scan_devices: {e}", exc_info=True)
            return {"tipo": "error", "mensaje": str(e)}
