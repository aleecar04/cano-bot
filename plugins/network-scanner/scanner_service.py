from __future__ import annotations

import ipaddress
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import netifaces
from scapy.all import ARP, Ether, srp

try:
    from mac_vendor_lookup import MacLookup

    _MAC_LOOKUP = MacLookup()
    try:
        _MAC_LOOKUP.update_vendors()
    except Exception:
        pass
    MAC_LOOKUP_AVAILABLE = True
except ImportError:
    MAC_LOOKUP_AVAILABLE = False
    print("[AVISO] mac-vendor-lookup no instalado. OUI desactivado.")

try:
    from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    print("[AVISO] zeroconf no instalado. mDNS desactivado.")


HOSTNAME_PATTERNS: dict[str, list[str]] = {
    "Luz":        ["hue", "light", "philips", "nanoleaf", "yeelight", "shelly"],
    "Altavoz":    ["echo", "dot", "alexa", "speaker", "homepod", "sonos"],
    "SmartTV":    ["samsung", "lg", "sony", "tcl", "roku", "chromecast", "shield", "firetv"],
    "Camara":     ["camera", "cam", "nest", "doorbell", "wyze", "ring"],
    "Ordenador":  ["macbook", "imac", "desktop", "laptop"],
    "Movil":      ["iphone", "ipad", "android", "pixel"],
    "Router":     ["router", "gateway", "firewall", "mikrotik", "ubiquiti"],
    "Impresora":  ["printer", "canon", "hp", "xerox", "brother"],
    "Termostato": ["thermostat", "nest", "ecobee", "honeywell"],
    "IoT":        ["tasmota", "esp8266", "esp32", "sonoff", "tuya", "homebridge"],
}

VENDOR_PATTERNS: dict[str, list[str]] = {
    "Luz":        ["signify", "philips lighting", "nanoleaf", "shelly"],
    "Router":     ["cisco", "mikrotik", "ubiquiti", "asus", "tp-link", "netgear",
                   "zyxel", "technicolor", "arcadyan", "sagemcom"],
    "Movil":      ["apple", "samsung electronics", "google", "xiaomi", "oneplus",
                   "huawei", "oppo", "vivo", "realme", "motorola"],
    "Ordenador":  ["intel", "dell", "lenovo", "hewlett packard", "apple",
                   "micro-star", "gigabyte", "asustek"],
    "IoT":        ["espressif", "tuya", "raspberry pi", "arduino"],
    "Camara":     ["hikvision", "dahua", "wyze", "ring", "axis", "hanwha"],
    "Impresora":  ["canon", "brother", "seiko epson", "xerox", "lexmark", "ricoh"],
    "SmartTV":    ["samsung", "lg electronics", "sony", "tcl", "hisense", "vizio"],
    "Altavoz":    ["sonos", "harman", "bose", "amazon technologies"],
    "Termostato": ["ecobee", "honeywell", "google"],
}

PORT_SIGNATURES: dict[int, Optional[str]] = {
    9100:  "Impresora",
    631:   "Impresora",
    515:   "Impresora",
    1883:  "IoT",
    8883:  "IoT",
    5683:  "IoT",
    1900:  "IoT",
    554:   "Camara",
    8554:  "Camara",
    37777: "Camara",
    34567: "Camara",
    1400:  "Altavoz",
    3400:  "Altavoz",
    55443: "Altavoz",
    8008:  "SmartTV",
    8009:  "SmartTV",
    9197:  "SmartTV",
    55000: "SmartTV",
    8080:  None,
    80:    None,
    443:   None,
    22:    "Ordenador",
    3389:  "Ordenador",
    548:   "Ordenador",
    445:   "Ordenador",
    139:   "Ordenador",
}
PORTS_TO_SCAN = list(PORT_SIGNATURES.keys())

MDNS_SIGNATURES: dict[str, str] = {
    "_hue._tcp.local.":             "Luz",
    "_homekit._tcp.local.":         "IoT",
    "_matter._tcp.local.":          "IoT",
    "_airplay._tcp.local.":         "SmartTV",
    "_raop._tcp.local.":            "Altavoz",
    "_sonos._tcp.local.":           "Altavoz",
    "_spotify-connect._tcp.local.": "Altavoz",
    "_googlecast._tcp.local.":      "SmartTV",
    "_ipp._tcp.local.":             "Impresora",
    "_ipps._tcp.local.":            "Impresora",
    "_pdl-datastream._tcp.local.":  "Impresora",
    "_printer._tcp.local.":         "Impresora",
    "_ssh._tcp.local.":             "Ordenador",
    "_smb._tcp.local.":             "Ordenador",
    "_afpovertcp._tcp.local.":      "Ordenador",
    "_nvstream_dbd._tcp.local.":    "Ordenador",
    "_rtsp._tcp.local.":            "Camara",
    "_daap._tcp.local.":            "Ordenador",
    "_sleep-proxy._udp.local.":     "Ordenador",
    "_ecobee._tcp.local.":          "Termostato",
    "_nest._tcp.local.":            "Termostato",
}
MDNS_SERVICE_TYPES = list(MDNS_SIGNATURES.keys())

WEIGHTS: dict[str, int] = {
    "hostname": 1,
    "vendor":   3,
    "port":     2,
    "mdns":     4,
}

SKIP_TYPES: frozenset[str] = frozenset({"Router"})

@dataclass
class DeviceInfo:
    ip: str
    mac: str
    mac_aleatoria: bool
    hostname: str
    fabricante: str
    tipo: str
    confianza: int
    puertos: list[int] = field(default_factory=list)
    mdns: list[str] = field(default_factory=list)
    deteccion: dict[str, str] = field(default_factory=dict)


def is_mac_randomized(mac: str) -> bool:
    try:
        return bool(int(mac.split(":")[0], 16) & 0x02)
    except (ValueError, IndexError):
        return False


def get_vendor(mac: str) -> Optional[str]:
    if not MAC_LOOKUP_AVAILABLE or is_mac_randomized(mac):
        return None
    try:
        return _MAC_LOOKUP.lookup(mac)
    except Exception:
        return None
    
class _MdnsCollector:
    """Recoge servicios mDNS anunciados en la red y los indexa por IP."""

    def __init__(self) -> None:
        self._services: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    # La firma debe coincidir con ServiceListener de zeroconf
    def add_service(self, zc: "Zeroconf", service_type: str, name: str) -> None:
        try:
            info = zc.get_service_info(service_type, name)
            if info and info.addresses:
                ip = socket.inet_ntoa(info.addresses[0])
                with self._lock:
                    self._services.setdefault(ip, [])
                    if service_type not in self._services[ip]:
                        self._services[ip].append(service_type)
        except Exception:
            pass

    def remove_service(self, zc: "Zeroconf", service_type: str, name: str) -> None:  # noqa: ARG002
        pass

    def update_service(self, zc: "Zeroconf", service_type: str, name: str) -> None:  # noqa: ARG002
        pass

    @property
    def results(self) -> dict[str, list[str]]:
        with self._lock:
            return {ip: list(svcs) for ip, svcs in self._services.items()}


def discover_mdns(timeout: int = 5) -> dict[str, list[str]]:
    if not ZEROCONF_AVAILABLE:
        return {}
    collector = _MdnsCollector()
    zc = Zeroconf()
    _browsers = [ServiceBrowser(zc, stype, collector) for stype in MDNS_SERVICE_TYPES]
    time.sleep(timeout)
    zc.close()
    return collector.results


def _check_port(ip: str, port: int, timeout: float, results: list[int], lock: threading.Lock) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            if s.connect_ex((ip, port)) == 0:
                with lock:
                    results.append(port)
    except Exception:
        pass


def scan_ports(ip: str, ports: list[int] = PORTS_TO_SCAN, timeout: float = 0.5) -> list[int]:
    open_ports: list[int] = []
    lock = threading.Lock()
    threads = [
        threading.Thread(target=_check_port, args=(ip, p, timeout, open_ports, lock), daemon=True)
        for p in ports
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return open_ports


def _score_hostname(hostname: str, scores: dict[str, int], breakdown: dict[str, str]) -> None:
    h = hostname.lower()
    for tipo, keywords in HOSTNAME_PATTERNS.items():
        if any(k in h for k in keywords):
            scores[tipo] = scores.get(tipo, 0) + WEIGHTS["hostname"]
            breakdown["hostname"] = f"{tipo} ('{hostname}')"
            return


def _score_vendor(vendor: str, scores: dict[str, int], breakdown: dict[str, str]) -> None:
    v = vendor.lower()
    for tipo, keywords in VENDOR_PATTERNS.items():
        if any(k in v for k in keywords):
            scores[tipo] = scores.get(tipo, 0) + WEIGHTS["vendor"]
            breakdown["vendor"] = f"{tipo} ('{vendor}')"
            return


def _score_ports(open_ports: list[int], scores: dict[str, int], breakdown: dict[str, str]) -> None:
    port_hits: list[str] = []
    for port in open_ports:
        tipo = PORT_SIGNATURES.get(port)
        if tipo:
            scores[tipo] = scores.get(tipo, 0) + WEIGHTS["port"]
            port_hits.append(f"{port}({tipo})")
    if port_hits:
        breakdown["ports"] = " ".join(port_hits)


def _score_mdns(mdns_services: list[str], scores: dict[str, int], breakdown: dict[str, str]) -> None:
    mdns_hits: list[str] = []
    for service in mdns_services:
        tipo = MDNS_SIGNATURES.get(service)
        if tipo:
            scores[tipo] = scores.get(tipo, 0) + WEIGHTS["mdns"]
            mdns_hits.append(service)
    if mdns_hits:
        breakdown["mdns"] = " ".join(mdns_hits)


def detect_device_type(
    hostname: Optional[str],
    vendor: Optional[str],
    open_ports: list[int],
    mdns_services: list[str],
    mac_randomized: bool = False,
) -> tuple[str, int, dict[str, str]]:
    scores: dict[str, int] = {}
    breakdown: dict[str, str] = {}

    if hostname:
        _score_hostname(hostname, scores, breakdown)

    if vendor:
        _score_vendor(vendor, scores, breakdown)
    elif mac_randomized:
        breakdown["vendor"] = "MAC aleatoria"

    _score_ports(open_ports, scores, breakdown)
    _score_mdns(mdns_services, scores, breakdown)

    if not scores:
        return "Dispositivo", 0, breakdown

    best = max(scores, key=lambda t: scores[t])
    return best, scores[best], breakdown


def get_local_network() -> tuple[Optional[str], Optional[str]]:
    try:
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET not in addrs:
                continue
            info = addrs[netifaces.AF_INET][0]
            ip, netmask = info.get("addr"), info.get("netmask")
            if ip and not ip.startswith("127.") and ip != "0.0.0.0":
                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                return ip, str(network)
    except Exception:
        pass
    return None, None


def _resolve_hostname(ip: str) -> Optional[str]:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None


def _build_device(ip: str, mac: str, mdns_map: dict[str, list[str]], scan_ports_flag: bool) -> Optional[DeviceInfo]:
    hostname = _resolve_hostname(ip)
    vendor = get_vendor(mac)
    randomized = is_mac_randomized(mac)
    open_p = scan_ports(ip) if scan_ports_flag else []
    mdns_svcs = mdns_map.get(ip, [])

    tipo, confianza, breakdown = detect_device_type(hostname, vendor, open_p, mdns_svcs, randomized)

    if tipo in SKIP_TYPES:
        return None

    return DeviceInfo(
        ip=ip,
        mac=mac,
        mac_aleatoria=randomized,
        hostname=hostname or ip,
        fabricante=vendor or ("desconocido (MAC aleatoria)" if randomized else "desconocido"),
        tipo=tipo,
        confianza=confianza,
        puertos=open_p,
        mdns=mdns_svcs,
        deteccion=breakdown,
    )


def scan_network(
    network: str,
    scan_ports_flag: bool = True,
    mdns_timeout: int = 5,
) -> list[DeviceInfo]:
    mdns_map: dict[str, list[str]] = {}

    mdns_thread: Optional[threading.Thread] = None
    if mdns_timeout > 0:
        def _mdns_worker() -> None:
            nonlocal mdns_map
            mdns_map = discover_mdns(mdns_timeout)
        mdns_thread = threading.Thread(target=_mdns_worker, daemon=True)
        mdns_thread.start()

    try:
        packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=network)
        arp_results = srp(packet, timeout=3, verbose=False)[0]
    except Exception as e:
        print(f"[ERROR] ARP sweep fallido: {e}")
        return []

    if mdns_thread:
        mdns_thread.join()

    devices: list[DeviceInfo] = []
    for _, received in arp_results:
        device = _build_device(received.psrc, received.hwsrc, mdns_map, scan_ports_flag)
        if device is not None:
            devices.append(device)

    return devices


def _print_device(d: DeviceInfo) -> None:
    rand_tag = " (MAC aleatoria)" if d.mac_aleatoria else ""
    print(f"\n{'-' * 55}")
    print(f"  IP         : {d.ip}")
    print(f"  MAC        : {d.mac}{rand_tag}")
    print(f"  Hostname   : {d.hostname}")
    print(f"  Fabricante : {d.fabricante}")
    print(f"  Tipo       : {d.tipo}")
    print(f"  Confianza  : {d.confianza}")
    if d.puertos:
        print(f"  Puertos    : {d.puertos}")
    if d.mdns:
        print(f"  mDNS       : {d.mdns}")
    if d.deteccion:
        print(f"  Evidencias : {d.deteccion}")


if __name__ == "__main__":
    my_ip, network = get_local_network()
    if not network:
        print("[ERROR] No se pudo detectar la red local.")
        raise SystemExit(1)

    print(f"[*] IP local : {my_ip}")
    print(f"[*] Red      : {network}")
    print(f"[*] Escaneando...")

    devices = scan_network(network, scan_ports_flag=True, mdns_timeout=5)

    print(f"\n[*] {len(devices)} dispositivo(s) encontrado(s)")
    for d in sorted(devices, key=lambda x: ipaddress.ip_address(x.ip)):
        _print_device(d)

    print(f"\n{'=' * 55}")