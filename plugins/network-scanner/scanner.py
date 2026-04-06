from errbot import BotPlugin, botcmd
import socket
import netifaces
from scapy.all import ARP, Ether, srp
import ipaddress
import json

from plugins._core import BasePlugin

class Scanner(BasePlugin, BotPlugin):

    def get_local_network(self):
        """Obtiene la red local del bot"""
        try:
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                addresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addresses:
                    addr_info = addresses[netifaces.AF_INET][0]
                    ip = addr_info.get('addr')
                    netmask = addr_info.get('netmask')

                    if ip and not ip.startswith('127.') and ip != '0.0.0.0':
                        network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                        self.log.info(f"Red detectada: {network} en interfaz {interface}")
                        return ip, str(network)
        except Exception as e:
            self.log.error(f"Error obteniendo red: {e}")
        return None, None

    def detect_device_type(self, hostname, ip):
        """Intenta deducir el tipo de dispositivo basándose en hostname y patrones conocidos"""
        if not hostname:
            return "Dispositivo"

        hostname_lower = hostname.lower()

        patterns = {
            "Luz":        ["hue", "light", "philips", "nanoleaf", "yeelight", "shelly"],
            "Altavoz":    ["echo", "dot", "alexa", "speaker", "homepod", "sonos"],
            "SmartTV":    ["samsung", "lg", "sony", "tcl", "roku", "chromecast", "shield", "firetv"],
            "Cámara":     ["camera", "cam", "nest", "doorbell", "wyze", "ring"],
            "Ordenador":  ["macbook", "imac", "desktop", "laptop", "pc"],
            "Móvil":      ["iphone", "ipad", "android", "pixel"],
            "Router":     ["router", "gateway", "firewall", "mikrotik", "ubiquiti"],
            "Impresora":  ["printer", "canon", "hp", "xerox", "brother"],
            "Termostato": ["thermostat", "nest", "ecobee", "honeywell"],
            "IoT":        ["tasmota", "esp8266", "esp32", "sonoff", "tuya", "homebridge"],
        }

        for device_type, keywords in patterns.items():
            if any(keyword in hostname_lower for keyword in keywords):
                return device_type

        return "Dispositivo"

    def scan_network(self, network):
        """Escanea la red usando ARP"""
        try:
            arp = ARP(pdst=network)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether / arp

            result = srp(packet, timeout=3, verbose=False)[0]

            dispositivos = []
            for sent, received in result:
                ip = received.psrc
                mac = received.hwsrc

                hostname = None
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except:
                    pass

                tipo = self.detect_device_type(hostname, ip)

                dispositivos.append({
                    "ip": ip,
                    "mac": mac,
                    "hostname": hostname or ip,
                    "tipo": tipo
                })

            self.log.info(f"ARP encontró {len(dispositivos)} dispositivos en {network}")
            return dispositivos
        except Exception as e:
            self.log.error(f"Error escaneando red: {e}")
            return []

    @botcmd
    def scan_devices(self, msg, args):
        """Escanea los dispositivos conectados a la red local
        Uso: scan_devices [red_cidr]
        Ejemplo: scan_devices 192.168.1.0/24
        """
        try:
            if args and args.strip():
                red = args.strip()
                ip_local = None
                self.log.info(f"Escaneando red especificada: {red}")
            else:
                ip_local, red = self.get_local_network()
                if not red:
                    return json.dumps({"tipo": "error", "mensaje": "No se pudo detectar la red local"})
                self.log.info(f"Red detectada: {red}, IP: {ip_local}")

            dispositivos = self.scan_network(red)
            self.log.info(f"Dispositivos encontrados: {len(dispositivos)}")

            respuesta_json = {
                "tipo": "scan_response",
                "red": red,
                "ip_bot": ip_local,
                "dispositivos": dispositivos,
                "total": len(dispositivos)
            }

            return json.dumps(respuesta_json)
        except Exception as e:
            self.log.error(f"Error en scan_devices: {e}", exc_info=True)
            return json.dumps({"tipo": "error", "mensaje": str(e)})

