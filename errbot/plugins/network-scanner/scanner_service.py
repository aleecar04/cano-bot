from __future__ import annotations

import ipaddress
import logging
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

import netifaces
from mac_vendor_lookup import MacLookup
from scapy.all import ARP, Ether, srp
from zeroconf import ServiceBrowser, Zeroconf

logger = logging.getLogger(__name__)

_MAC_LOOKUP = MacLookup()
_MAC_VENDORS_UPDATED = False
_MAC_VENDORS_LOCK = threading.Lock()


def _ensure_mac_vendors_loaded() -> None:
    global _MAC_VENDORS_UPDATED
    if _MAC_VENDORS_UPDATED:
        return
    with _MAC_VENDORS_LOCK:
        if _MAC_VENDORS_UPDATED:
            return
        try:
            _MAC_LOOKUP.update_vendors()
        except Exception:
            pass
        _MAC_VENDORS_UPDATED = True


HOSTNAME_PATTERNS: dict[str, list[str]] = {
    "Luz":       ["hue", "light", "philips", "nanoleaf", "yeelight"],
    "Enchufe":   ["kasa", "meross"],
    "Altavoz":   ["echo", "dot", "alexa", "speaker", "homepod", "sonos"],
    "SmartTV":   ["samsung", "lg", "sony", "tcl", "roku", "chromecast", "firetv"],
    "IoT":       ["tasmota", "esp8266", "esp32", "sonoff", "tuya", "homebridge"],
    "Ordenador": ["macbook", "imac", "desktop", "laptop"],
    "Movil":     ["iphone", "ipad", "android", "pixel"],
    "Router":    ["router", "gateway", "firewall", "mikrotik", "ubiquiti"],
}

VENDOR_PATTERNS: dict[str, list[str]] = {
    "Luz":       ["signify", "philips lighting", "nanoleaf"],
    "Enchufe":   ["tp-link kasa", "meross"],
    "IoT":       ["espressif", "tuya", "beken", "lsec", "realtek semiconductor",
                  "raspberry pi", "arduino", "shenzhen bailing"],
    "SmartTV":   ["samsung", "lg electronics", "sony", "tcl", "hisense", "vizio"],
    "Altavoz":   ["sonos", "harman", "bose", "amazon technologies"],
    "Router":    ["cisco", "mikrotik", "ubiquiti", "asus", "tp-link", "netgear",
                  "zyxel", "technicolor", "arcadyan", "sagemcom"],
    "Movil":     ["apple", "samsung electronics", "google", "xiaomi", "oneplus",
                  "huawei", "oppo", "vivo", "realme", "motorola"],
    "Ordenador": ["intel", "dell", "lenovo", "hewlett packard", "apple",
                  "micro-star", "gigabyte", "asustek"],
}

MDNS_SIGNATURES: dict[str, str] = {
    "_hue._tcp.local.":             "Luz",
    "_homekit._tcp.local.":         "IoT",
    "_matter._tcp.local.":          "IoT",
    "_airplay._tcp.local.":         "SmartTV",
    "_googlecast._tcp.local.":      "SmartTV",
    "_sonos._tcp.local.":           "Altavoz",
    "_raop._tcp.local.":            "Altavoz",
    "_spotify-connect._tcp.local.": "Altavoz",
}
MDNS_SERVICE_TYPES = list(MDNS_SIGNATURES.keys())

_WEIGHT_HOSTNAME = 1
_WEIGHT_VENDOR   = 3
_WEIGHT_MDNS     = 4

SKIP_TYPES: frozenset[str] = frozenset({"Router"})


@dataclass
class DeviceInfo:
    ip: str
    mac: str
    hostname: str
    tipo: str


def is_mac_randomized(mac: str) -> bool:
    try:
        return bool(int(mac.split(":")[0], 16) & 0x02)
    except (ValueError, IndexError):
        return False


def get_vendor(mac: str) -> Optional[str]:
    if is_mac_randomized(mac):
        return None
    _ensure_mac_vendors_loaded()
    try:
        return _MAC_LOOKUP.lookup(mac)
    except Exception:
        return None


class _MdnsCollector:

    def __init__(self) -> None:
        self._services: dict[str, list[str]] = {}
        self._lock = threading.Lock()

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
    collector = _MdnsCollector()
    zc = Zeroconf()
    _browsers = [ServiceBrowser(zc, stype, collector) for stype in MDNS_SERVICE_TYPES]
    time.sleep(timeout)
    zc.close()
    return collector.results


def _match_pattern(value: str, patterns: dict[str, list[str]], weight: int,
                   scores: dict[str, int]) -> None:
    if not value:
        return
    v = value.lower()
    for tipo, keywords in patterns.items():
        if any(k in v for k in keywords):
            scores[tipo] = scores.get(tipo, 0) + weight
            return


def _match_mdns(services: list[str], scores: dict[str, int]) -> None:
    for service in services:
        tipo = MDNS_SIGNATURES.get(service)
        if tipo:
            scores[tipo] = scores.get(tipo, 0) + _WEIGHT_MDNS


def detect_device_type(hostname: Optional[str], vendor: Optional[str],
                       mdns_services: list[str]) -> str:
    scores: dict[str, int] = {}
    _match_pattern(hostname or "", HOSTNAME_PATTERNS, _WEIGHT_HOSTNAME, scores)
    if vendor:
        _match_pattern(vendor, VENDOR_PATTERNS, _WEIGHT_VENDOR, scores)
    _match_mdns(mdns_services, scores)
    if not scores:
        return "Dispositivo"
    return max(scores, key=lambda t: scores[t])


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


def _resolve_hostname(ip: str, timeout: float = 1.0) -> Optional[str]:
    result: list = [None]

    def _do_resolve() -> None:
        try:
            result[0] = socket.gethostbyaddr(ip)[0]
        except Exception:
            pass

    t = threading.Thread(target=_do_resolve, daemon=True)
    t.start()
    t.join(timeout=timeout)
    return result[0]


def _build_device(ip: str, mac: str, mdns_map: dict[str, list[str]]) -> Optional[DeviceInfo]:
    hostname = _resolve_hostname(ip)
    vendor   = get_vendor(mac)
    tipo     = detect_device_type(hostname, vendor, mdns_map.get(ip, []))

    if tipo in SKIP_TYPES:
        return None

    return DeviceInfo(ip=ip, mac=mac, hostname=hostname or ip, tipo=tipo)


def scan_network(
    network: str,
    mdns_timeout: int = 5,
    max_workers: int = 20,
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
    except Exception:
        logger.exception("ARP sweep fallido")
        return []

    if mdns_thread:
        mdns_thread.join()

    hosts = [(received.psrc, received.hwsrc) for _, received in arp_results]
    if not hosts:
        return []

    devices: list[DeviceInfo] = []
    with ThreadPoolExecutor(max_workers=min(len(hosts), max_workers)) as pool:
        futures = {
            pool.submit(_build_device, ip, mac, mdns_map): ip
            for ip, mac in hosts
        }
        for fut in as_completed(futures):
            try:
                device = fut.result()
                if device is not None:
                    devices.append(device)
            except Exception as e:
                logger.warning(f"Error building device {futures[fut]}: {e}")

    return devices


