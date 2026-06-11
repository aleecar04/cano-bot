import socket
from unittest.mock import MagicMock, patch

import pytest

import scanner_service
from scanner_service import (
    _MdnsCollector,
    _build_device,
    _match_pattern,
    _resolve_hostname,
    detect_device_type,
    get_local_network,
    get_vendor,
    is_mac_randomized,
    scan_network,
)


class TestScannerService:

    @pytest.mark.parametrize("mac, expected", [
        ("02:11:22:33:44:55", True),
        ("no-es-mac", False),
    ])
    def test_is_mac_randomized(self, mac, expected):
        assert is_mac_randomized(mac) is expected

    def test_get_vendor_lookup_failure_returns_none(self):
        with patch.object(scanner_service._MAC_LOOKUP, "lookup", side_effect=KeyError("no")), \
             patch("scanner_service._ensure_mac_vendors_loaded"):
            assert get_vendor("00:11:22:33:44:55") is None

    def test_ensure_mac_vendors_loaded_updates_only_once_per_session(self):
        scanner_service._MAC_VENDORS_UPDATED = False
        with patch.object(scanner_service._MAC_LOOKUP, "update_vendors") as mock_u:
            scanner_service._ensure_mac_vendors_loaded()
            scanner_service._ensure_mac_vendors_loaded()
        mock_u.assert_called_once()

    def test_match_pattern_scores_on_keyword_hit(self):
        scores: dict = {}
        _match_pattern("PHILIPS-LIGHT-1", {"Luz": ["hue", "philips"], "TV": ["sony"]}, 3, scores)
        assert scores == {"Luz": 3}

    @pytest.mark.parametrize("hostname, vendor, mdns, expected", [
        (None, None, [], "Dispositivo"),
        (None, "sony", ["_hue._tcp.local."], "Luz"),
    ])
    def test_detect_device_type_uses_scoring(self, hostname, vendor, mdns, expected):
        assert detect_device_type(hostname, vendor, mdns) == expected

    def test_mdns_add_service_indexes_by_ip_dedupes(self):
        c = _MdnsCollector()
        zc = MagicMock()
        info = MagicMock()
        info.addresses = [socket.inet_aton("192.168.1.10")]
        zc.get_service_info.return_value = info
        c.add_service(zc, "_hue._tcp.local.", "name")
        c.add_service(zc, "_hue._tcp.local.", "name")
        assert c.results == {"192.168.1.10": ["_hue._tcp.local."]}

    def test_get_local_network_returns_subnet_of_active_interface(self):
        with patch.object(scanner_service.netifaces, "interfaces", return_value=["eth0"]), \
             patch.object(scanner_service.netifaces, "ifaddresses",
                          return_value={scanner_service.netifaces.AF_INET: [
                              {"addr": "192.168.1.50", "netmask": "255.255.255.0"}
                          ]}):
            ip, net = scanner_service.get_local_network()
        assert ip == "192.168.1.50" and "192.168.1.0/24" in net

    def test_get_local_network_silences_exceptions_and_returns_none(self):
        with patch("scanner_service.netifaces.interfaces", side_effect=RuntimeError("boom")):
            assert get_local_network() == (None, None)

    @pytest.mark.parametrize("gethostbyaddr_side_effect, expected", [
        ({"return_value": ("h.local", [], [])}, "h.local"),
        ({"side_effect": OSError},               None),
    ])
    def test_resolve_hostname_uses_dns_or_returns_none(self, gethostbyaddr_side_effect, expected):
        with patch("scanner_service.socket.gethostbyaddr", **gethostbyaddr_side_effect):
            assert _resolve_hostname("192.168.1.10") == expected

    def test_build_device_builds_device_using_classification(self):
        with patch("scanner_service._resolve_hostname", return_value="hue-bridge"), \
             patch("scanner_service.get_vendor", return_value="Signify"):
            dev = _build_device("192.168.1.10", "00:11:22:33:44:55", {})
        assert dev.ip == "192.168.1.10" and dev.tipo == "Luz"

    @pytest.mark.parametrize("srp_kwargs", [
        {"side_effect": RuntimeError("no privs")},
        {"return_value": ([], [])},
    ])
    def test_scan_network_returns_empty_when_arp_fails_or_no_hosts(self, srp_kwargs):
        with patch("scanner_service.srp", **srp_kwargs):
            assert scan_network("192.168.1.0/24", mdns_timeout=0) == []

    @pytest.mark.parametrize("build_return, expected_count", [
        (MagicMock(ip="192.168.1.10"), 1),
        (None,                          0),
    ])
    def test_scan_network_filters_devices_based_on_build_result(self, build_return, expected_count):
        received = MagicMock()
        received.psrc = "192.168.1.10"
        received.hwsrc = "00:11:22:33:44:55"
        with patch("scanner_service.srp", return_value=([(None, received)], [])), \
             patch("scanner_service._build_device", return_value=build_return):
            assert len(scan_network("192.168.1.0/24", mdns_timeout=0)) == expected_count
