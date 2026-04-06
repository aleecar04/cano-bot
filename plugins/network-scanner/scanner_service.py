import socket
import netifaces
import ipaddress
from scapy.all import ARP, Ether, srp

DEVICE_PATTERNS = {
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


def get_local_network() -> tuple[str | None, str | None]:
    try:
        for interface in netifaces.interfaces():
            addresses = netifaces.ifaddresses(interface)
            if netifaces.AF_INET not in addresses:
                continue
            addr_info = addresses[netifaces.AF_INET][0]
            ip = addr_info.get("addr")
            netmask = addr_info.get("netmask")
            if ip and not ip.startswith("127.") and ip != "0.0.0.0":
                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                return ip, str(network)
    except Exception:
        pass
    return None, None


def detect_device_type(hostname: str | None) -> str:
    if not hostname:
        return "Dispositivo"
    hostname_lower = hostname.lower()
    for device_type, keywords in DEVICE_PATTERNS.items():
        if any(keyword in hostname_lower for keyword in keywords):
            return device_type
    return "Dispositivo"


def scan_network(network: str) -> list[dict]:
    try:
        packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=network)
        result = srp(packet, timeout=3, verbose=False)[0]

        dispositivos = []
        for _, received in result:
            ip = received.psrc
            hostname = _resolve_hostname(ip)
            dispositivos.append({
                "ip": ip,
                "mac": received.hwsrc,
                "hostname": hostname or ip,
                "tipo": detect_device_type(hostname)
            })
        return dispositivos
    except Exception:
        return []


def _resolve_hostname(ip: str) -> str | None:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None