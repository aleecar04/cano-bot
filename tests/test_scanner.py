"""
Tests for plugins/network-scanner/scanner_service.py

Only the pure classification logic is tested (no network, no ARP, no scapy).
"""
import pytest
# scanner_service lives in plugins/network-scanner/ (hyphen → not a valid package name)
# conftest.py adds that directory to sys.path so we can import it directly.
from scanner_service import (  # type: ignore[import]
    detect_device_type,
    is_mac_randomized,
    _score_hostname,
    _score_vendor,
    _score_ports,
    _score_mdns,
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
