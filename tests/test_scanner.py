"""
Tests for plugins/network-scanner/scanner_service.py

Only the pure classification logic is tested (no network, no ARP, no scapy).
"""
import pytest
# scanner_service lives in plugins/network-scanner/ (hyphen → not a valid package name)
# conftest.py adds that directory to sys.path so we can import it directly.
from unittest.mock import MagicMock, patch

from scanner_service import (  # type: ignore[import]
    detect_device_type,
    is_mac_randomized,
    _score_hostname,
    _score_vendor,
    _score_ports,
    _score_mdns,
    get_local_network,
    _resolve_hostname,
    _build_device,
    WEIGHTS,
    SKIP_TYPES,
)


# ── is_mac_randomized ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("mac, expected", [
    ("02:00:00:00:00:00", True),   # locally administered bit set
    ("06:ab:cd:ef:01:23", True),   # locally administered bit set
    ("00:1A:2B:3C:4D:5E", False),  # normal OUI
    ("dc:a6:32:00:00:00", False),  # Raspberry Pi OUI
    ("aa:bb:cc:dd:ee:ff", True),   # bit 1 of first octet set (0xaa = 0b10101010)
])
def test_is_mac_randomized(mac, expected):
    assert is_mac_randomized(mac) is expected


# ── Hostname scoring ──────────────────────────────────────────────────────────

def test_score_hostname_samsung_tv():
    scores, breakdown = {}, {}
    _score_hostname("samsung-tv-living", scores, breakdown)
    assert scores.get("SmartTV", 0) == WEIGHTS["hostname"]
    assert "hostname" in breakdown


def test_score_hostname_philips_hue():
    scores, breakdown = {}, {}
    _score_hostname("Philips-Hue-Bridge", scores, breakdown)
    assert scores.get("Luz", 0) == WEIGHTS["hostname"]


def test_score_hostname_no_match():
    scores, breakdown = {}, {}
    _score_hostname("random-device-abc123", scores, breakdown)
    assert scores == {}


def test_score_hostname_case_insensitive():
    scores, breakdown = {}, {}
    _score_hostname("CHROMECAST", scores, breakdown)
    assert scores.get("SmartTV", 0) > 0


# ── Vendor scoring ────────────────────────────────────────────────────────────

def test_score_vendor_apple_mobile():
    scores, breakdown = {}, {}
    _score_vendor("Apple, Inc.", scores, breakdown)
    assert scores.get("Movil", 0) == WEIGHTS["vendor"]


def test_score_vendor_cisco_router():
    scores, breakdown = {}, {}
    _score_vendor("Cisco Systems", scores, breakdown)
    assert scores.get("Router", 0) == WEIGHTS["vendor"]


def test_score_vendor_espressif_iot():
    scores, breakdown = {}, {}
    _score_vendor("Espressif Inc.", scores, breakdown)
    assert scores.get("IoT", 0) == WEIGHTS["vendor"]


def test_score_vendor_no_match():
    scores, breakdown = {}, {}
    _score_vendor("Unknown Vendor XYZ", scores, breakdown)
    assert scores == {}


# ── Port scoring ──────────────────────────────────────────────────────────────

def test_score_ports_printer_ports():
    scores, breakdown = {}, {}
    _score_ports([9100, 631], scores, breakdown)
    assert scores.get("Impresora", 0) == WEIGHTS["port"] * 2


def test_score_ports_smart_tv():
    scores, breakdown = {}, {}
    _score_ports([8008], scores, breakdown)
    assert scores.get("SmartTV", 0) == WEIGHTS["port"]


def test_score_ports_generic_ports_ignored():
    """Ports like 80 and 443 have no device type (None) and must not add score."""
    scores, breakdown = {}, {}
    _score_ports([80, 443, 8080], scores, breakdown)
    assert scores == {}


def test_score_ports_empty():
    scores, breakdown = {}, {}
    _score_ports([], scores, breakdown)
    assert scores == {}


# ── mDNS scoring ──────────────────────────────────────────────────────────────

def test_score_mdns_googlecast():
    scores, breakdown = {}, {}
    _score_mdns(["_googlecast._tcp.local."], scores, breakdown)
    assert scores.get("SmartTV", 0) == WEIGHTS["mdns"]


def test_score_mdns_printer():
    scores, breakdown = {}, {}
    _score_mdns(["_ipp._tcp.local.", "_printer._tcp.local."], scores, breakdown)
    assert scores.get("Impresora", 0) == WEIGHTS["mdns"] * 2


def test_score_mdns_unknown_service():
    scores, breakdown = {}, {}
    _score_mdns(["_something-unknown._tcp.local."], scores, breakdown)
    assert scores == {}


# ── detect_device_type ────────────────────────────────────────────────────────

def test_detect_no_signals_returns_dispositivo():
    tipo, confianza, _ = detect_device_type(None, None, [], [])
    assert tipo == "Dispositivo"
    assert confianza == 0


def test_detect_hostname_only():
    tipo, confianza, _ = detect_device_type("lg-smart-tv", None, [], [])
    assert tipo == "SmartTV"
    assert confianza == WEIGHTS["hostname"]


def test_detect_vendor_beats_hostname_different_types():
    """Vendor weight (3) beats hostname weight (1) when they disagree."""
    # hostname → Luz (weight 1), vendor → SmartTV (weight 3)
    # "LG Electronics" contains "lg electronics" which is in VENDOR_PATTERNS["SmartTV"]
    tipo, confianza, _ = detect_device_type("hue-light", "LG Electronics", [], [])
    assert tipo == "SmartTV"
    assert confianza >= WEIGHTS["vendor"]


def test_detect_mdns_has_highest_weight():
    """mDNS (weight 4) should win over a conflicting hostname (weight 1)."""
    tipo, confianza, _ = detect_device_type(
        "hp-printer",           # → Impresora (1)
        None,
        [],
        ["_googlecast._tcp.local."],  # → SmartTV (4)
    )
    assert tipo == "SmartTV"


def test_detect_combined_signals_accumulate():
    """Multiple signals for the same type accumulate their scores."""
    # "LG Electronics" → SmartTV (VENDOR_PATTERNS["SmartTV"] contains "lg electronics")
    tipo, confianza, _ = detect_device_type(
        "lg-smart-tv",          # SmartTV +1  (hostname contains "lg")
        "LG Electronics",       # SmartTV +3
        [8008],                 # SmartTV +2
        [],
    )
    assert tipo == "SmartTV"
    assert confianza == WEIGHTS["hostname"] + WEIGHTS["vendor"] + WEIGHTS["port"]


def test_detect_router_is_valid_result():
    """detect_device_type CAN return Router; SKIP_TYPES filtering happens in _build_device."""
    tipo, _, _ = detect_device_type("mikrotik-router", "MikroTik", [], [])
    assert tipo == "Router"
    assert "Router" in SKIP_TYPES


def test_detect_breakdown_populated():
    _, _, breakdown = detect_device_type("lg-tv", "LG Electronics", [8009], [])
    assert "hostname" in breakdown or "vendor" in breakdown or "ports" in breakdown


# ── is_mac_randomized edge cases ──────────────────────────────────────────────

def test_is_mac_randomized_empty_string_returns_false():
    # IndexError when split gives empty list
    assert is_mac_randomized("") is False


def test_is_mac_randomized_non_hex_byte_returns_false():
    # ValueError from int("zz", 16)
    assert is_mac_randomized("zz:00:00:00:00:00") is False


# ── get_vendor ────────────────────────────────────────────────────────────────

def test_get_vendor_randomized_mac_returns_none():
    from scanner_service import get_vendor
    # MAC with locally administered bit → always None regardless of lookup
    assert get_vendor("02:00:00:00:00:00") is None


def test_get_vendor_lookup_success():
    from scanner_service import get_vendor, _MAC_LOOKUP, MAC_LOOKUP_AVAILABLE
    if not MAC_LOOKUP_AVAILABLE:
        pytest.skip("MAC lookup not available")
    _MAC_LOOKUP.lookup.return_value = "Raspberry Pi Foundation"
    result = get_vendor("dc:a6:32:00:00:00")  # non-randomized MAC
    assert result is not None


def test_get_vendor_lookup_exception_returns_none():
    from scanner_service import get_vendor, _MAC_LOOKUP, MAC_LOOKUP_AVAILABLE
    if not MAC_LOOKUP_AVAILABLE:
        pytest.skip("MAC lookup not available")
    _MAC_LOOKUP.lookup.side_effect = Exception("unknown OUI")
    result = get_vendor("dc:a6:32:00:00:00")
    assert result is None
    _MAC_LOOKUP.lookup.side_effect = None  # restore for other tests


# ── Additional _score_hostname patterns ───────────────────────────────────────

def test_score_hostname_echo_is_altavoz():
    scores, breakdown = {}, {}
    _score_hostname("amazon-echo-dot", scores, breakdown)
    assert scores.get("Altavoz", 0) == WEIGHTS["hostname"]


def test_score_hostname_nest_cam_is_camara():
    scores, breakdown = {}, {}
    _score_hostname("nest-cam-outdoor", scores, breakdown)
    assert scores.get("Camara", 0) == WEIGHTS["hostname"]


def test_score_hostname_esp32_is_iot():
    scores, breakdown = {}, {}
    _score_hostname("esp32-device", scores, breakdown)
    assert scores.get("IoT", 0) == WEIGHTS["hostname"]


# ── Additional _score_vendor patterns ────────────────────────────────────────

def test_score_vendor_raspberry_pi_is_iot():
    scores, breakdown = {}, {}
    _score_vendor("Raspberry Pi Foundation", scores, breakdown)
    assert scores.get("IoT", 0) == WEIGHTS["vendor"]


def test_score_vendor_sonos_is_altavoz():
    scores, breakdown = {}, {}
    _score_vendor("Sonos, Inc.", scores, breakdown)
    assert scores.get("Altavoz", 0) == WEIGHTS["vendor"]


# ── Additional _score_mdns patterns ──────────────────────────────────────────

def test_score_mdns_airplay_is_smarttv():
    scores, breakdown = {}, {}
    _score_mdns(["_airplay._tcp.local."], scores, breakdown)
    assert scores.get("SmartTV", 0) == WEIGHTS["mdns"]


def test_score_mdns_ssh_is_ordenador():
    scores, breakdown = {}, {}
    _score_mdns(["_ssh._tcp.local."], scores, breakdown)
    assert scores.get("Ordenador", 0) == WEIGHTS["mdns"]


# ── Additional detect_device_type ─────────────────────────────────────────────

def test_detect_altavoz_all_signals():
    tipo, confianza, _ = detect_device_type(
        "sonos-living-room",            # Altavoz +1
        "Sonos, Inc.",                  # Altavoz +3
        [1400],                         # Altavoz +2
        ["_raop._tcp.local."],          # Altavoz +4
    )
    assert tipo == "Altavoz"
    assert confianza == WEIGHTS["hostname"] + WEIGHTS["vendor"] + WEIGHTS["port"] + WEIGHTS["mdns"]


def test_detect_impresora_all_signals():
    tipo, _, _ = detect_device_type(
        "hp-laserjet",
        "HP Inc.",
        [9100],
        ["_ipp._tcp.local."],
    )
    assert tipo == "Impresora"


# ── detect_device_type edge cases ────────────────────────────────────────────

def test_detect_mac_aleatoria_sin_vendor():
    """mac_randomized=True + no vendor → breakdown includes 'MAC aleatoria'."""
    _, _, breakdown = detect_device_type(None, None, [], [], mac_randomized=True)
    assert "MAC aleatoria" in breakdown.get("vendor", "")


def test_detect_no_signals_returns_dispositivo():
    tipo, confianza, _ = detect_device_type(None, None, [], [])
    assert tipo == "Dispositivo"
    assert confianza == 0


# ── get_local_network ─────────────────────────────────────────────────────────

def test_get_local_network_returns_none_when_no_interfaces():
    import sys
    netifaces_mock = sys.modules["netifaces"]
    netifaces_mock.interfaces.return_value = []
    ip, net = get_local_network()
    assert ip is None
    assert net is None


def test_get_local_network_returns_ip_and_network():
    import sys, ipaddress
    netifaces_mock = sys.modules["netifaces"]
    netifaces_mock.interfaces.return_value = ["eth0"]
    netifaces_mock.AF_INET = 2
    netifaces_mock.ifaddresses.return_value = {
        2: [{"addr": "192.168.1.10", "netmask": "255.255.255.0"}]
    }
    ip, net = get_local_network()
    assert ip == "192.168.1.10"
    assert "192.168.1.0/24" in net


def test_get_local_network_skips_loopback():
    import sys
    netifaces_mock = sys.modules["netifaces"]
    netifaces_mock.interfaces.return_value = ["lo"]
    netifaces_mock.AF_INET = 2
    netifaces_mock.ifaddresses.return_value = {
        2: [{"addr": "127.0.0.1", "netmask": "255.0.0.0"}]
    }
    ip, net = get_local_network()
    assert ip is None


# ── _resolve_hostname ─────────────────────────────────────────────────────────

def test_resolve_hostname_returns_name():
    with patch("socket.gethostbyaddr", return_value=("mydevice.local", [], ["192.168.1.5"])):
        result = _resolve_hostname("192.168.1.5", timeout=2.0)
    assert result == "mydevice.local"


def test_resolve_hostname_returns_none_on_error():
    with patch("socket.gethostbyaddr", side_effect=Exception("no host")):
        result = _resolve_hostname("192.168.1.99", timeout=2.0)
    assert result is None


# ── _build_device ─────────────────────────────────────────────────────────────

def test_build_device_returns_device_info():
    with patch("scanner_service._resolve_hostname", return_value="shelly-plug"), \
         patch("scanner_service.get_vendor", return_value="Allterco Robotics"), \
         patch("scanner_service.is_mac_randomized", return_value=False), \
         patch("scanner_service.scan_ports", return_value=[80]):
        result = _build_device(
            "192.168.1.20", "AA:BB:CC:DD:EE:FF", {}, scan_ports_flag=True
        )
    assert result is not None
    assert result.ip == "192.168.1.20"


def test_build_device_returns_none_for_skip_type():
    """If detected type is in SKIP_TYPES, _build_device returns None."""
    with patch("scanner_service._resolve_hostname", return_value=None), \
         patch("scanner_service.get_vendor", return_value=None), \
         patch("scanner_service.is_mac_randomized", return_value=False), \
         patch("scanner_service.scan_ports", return_value=[]), \
         patch("scanner_service.detect_device_type",
               return_value=(next(iter(SKIP_TYPES)), 0, {})):
        result = _build_device("10.0.0.1", "02:00:00:00:00:01", {}, False)
    assert result is None


def test_build_device_no_port_scan():
    """scan_ports_flag=False → scan_ports not called."""
    with patch("scanner_service._resolve_hostname", return_value="router"), \
         patch("scanner_service.get_vendor", return_value="TP-Link"), \
         patch("scanner_service.is_mac_randomized", return_value=False), \
         patch("scanner_service.scan_ports") as mock_scan:
        _build_device("10.0.0.1", "AA:00:00:00:00:01", {}, scan_ports_flag=False)
    mock_scan.assert_not_called()


# ── get_local_network exception path ─────────────────────────────────────────

def test_get_local_network_exception_returns_none():
    import sys
    netifaces_mock = sys.modules["netifaces"]
    netifaces_mock.interfaces.side_effect = Exception("hardware error")
    ip, net = get_local_network()
    assert ip is None
    assert net is None
    netifaces_mock.interfaces.side_effect = None  # reset


# ── scan_simulation_devices ───────────────────────────────────────────────────

def test_scan_simulation_finds_shelly_device():
    from scanner_service import scan_simulation_devices
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"type": "SHPLG-S", "mac": "AABBCCDDEEFF"}

    def fake_get(url, timeout=None):
        if "8181" in url:
            return mock_resp
        raise Exception("connection refused")

    with patch("requests.get", side_effect=fake_get):
        devices = scan_simulation_devices(port_start=8181, port_end=8183)
    assert len(devices) == 1
    assert devices[0].ip == "127.0.0.1"


def test_scan_simulation_skips_non_200():
    from scanner_service import scan_simulation_devices
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch("requests.get", return_value=mock_resp):
        devices = scan_simulation_devices(port_start=8181, port_end=8182)
    assert devices == []


def test_scan_simulation_handles_connection_error():
    from scanner_service import scan_simulation_devices
    with patch("requests.get", side_effect=Exception("refused")):
        devices = scan_simulation_devices(port_start=8181, port_end=8182)
    assert devices == []
