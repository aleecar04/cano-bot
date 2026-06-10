import socket
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.parametrize("mac, expected", [
    ("02:11:22:33:44:55", True),
    ("no-es-mac", False),
])
def test_is_mac_randomized(mac, expected):
    from scanner_service import is_mac_randomized
    assert is_mac_randomized(mac) is expected


class TestGetVendor:

    def test_normal_mac_queries_oui_database(self):
        import scanner_service
        with patch.object(scanner_service._MAC_LOOKUP, "lookup", return_value="Apple, Inc."), \
             patch("scanner_service._ensure_mac_vendors_loaded"):
            assert scanner_service.get_vendor("00:11:22:33:44:55") == "Apple, Inc."

    def test_lookup_failure_returns_none(self):
        import scanner_service
        with patch.object(scanner_service._MAC_LOOKUP, "lookup", side_effect=KeyError("no")), \
             patch("scanner_service._ensure_mac_vendors_loaded"):
            assert scanner_service.get_vendor("00:11:22:33:44:55") is None


class TestEnsureMacVendorsLoaded:

    def test_updates_only_once_per_session(self):
        import scanner_service
        scanner_service._MAC_VENDORS_UPDATED = False
        with patch.object(scanner_service._MAC_LOOKUP, "update_vendors") as mock_u:
            scanner_service._ensure_mac_vendors_loaded()
            scanner_service._ensure_mac_vendors_loaded()
        mock_u.assert_called_once()

@pytest.mark.parametrize("value, expected_score", [
    ("", {}),
    ("PHILIPS-LIGHT-1", {"Luz": 3})
])
def test_match_pattern_matches_first_keyword_case_insensitive(value, expected_score):
    from scanner_service import _match_pattern
    scores: dict = {}
    _match_pattern(value, {"Luz": ["hue", "philips"], "TV": ["samsung"]}, 3, scores)
    assert scores == expected_score


@pytest.mark.parametrize("hostname, vendor, mdns, expected", [
    (None, None, [], "Dispositivo"),
    (None, "samsung", ["_hue._tcp.local."], "Luz"),
])
def test_detect_device_type_applies_weighted_scoring(hostname, vendor, mdns, expected):
    from scanner_service import detect_device_type
    assert detect_device_type(hostname, vendor, mdns) == expected


class TestMdnsCollector:

    def _client_with_info(self, addr="192.168.1.10"):
        from scanner_service import _MdnsCollector
        c = _MdnsCollector()
        zc = MagicMock()
        info = MagicMock()
        info.addresses = [socket.inet_aton(addr)]
        zc.get_service_info.return_value = info
        return c, zc

    def test_add_service_indexes_by_ip_and_dedupes(self):
        c, zc = self._client_with_info()
        c.add_service(zc, "_hue._tcp.local.", "name")
        c.add_service(zc, "_hue._tcp.local.", "name")
        assert c.results == {"192.168.1.10": ["_hue._tcp.local."]}

class TestNetworkInfo:

    def test_get_local_network_returns_valid_subnet(self):
        import scanner_service
        with patch.object(scanner_service.netifaces, "interfaces", return_value=["eth0"]), \
             patch.object(scanner_service.netifaces, "ifaddresses",
                          return_value={scanner_service.netifaces.AF_INET: [
                              {"addr": "192.168.1.50", "netmask": "255.255.255.0"}
                          ]}):
            ip, net = scanner_service.get_local_network()
        assert ip == "192.168.1.50" and "192.168.1.0/24" in net

    def test_get_local_network_returns_none_on_exception(self):
        with patch("scanner_service.netifaces.interfaces", side_effect=RuntimeError("boom")):
            from scanner_service import get_local_network
            assert get_local_network() == (None, None)

    def test_resolve_hostname_returns_name_or_none_on_oserror(self):
        from scanner_service import _resolve_hostname
        with patch("scanner_service.socket.gethostbyaddr", return_value=("h.local", [], [])):
            assert _resolve_hostname("192.168.1.10") == "h.local"
        with patch("scanner_service.socket.gethostbyaddr", side_effect=OSError):
            assert _resolve_hostname("192.168.1.10") is None


class TestBuildDevice:

    def test_returns_none_for_skipped_types_like_router(self):
        with patch("scanner_service._resolve_hostname", return_value="router-1"), \
             patch("scanner_service.get_vendor", return_value="Cisco Systems"):
            from scanner_service import _build_device
            assert _build_device("192.168.1.1", "00:11:22:33:44:55", {}) is None

    def test_builds_device_using_classification(self):
        with patch("scanner_service._resolve_hostname", return_value="hue-bridge"), \
             patch("scanner_service.get_vendor", return_value="Signify"):
            from scanner_service import _build_device
            dev = _build_device("192.168.1.10", "00:11:22:33:44:55", {})
        assert dev.ip == "192.168.1.10" and dev.tipo == "Luz"

class TestScanNetwork:

    @pytest.mark.parametrize("srp_kwargs", [
        {"side_effect": RuntimeError("no privs")},
        {"return_value": ([], [])},
    ])
    def test_returns_empty_when_arp_fails_or_no_hosts(self, srp_kwargs):
        with patch("scanner_service.srp", **srp_kwargs):
            from scanner_service import scan_network
            assert scan_network("192.168.1.0/24", mdns_timeout=0) == []

    def test_builds_devices_from_arp_responses(self):
        received = MagicMock()
        received.psrc = "192.168.1.10"
        received.hwsrc = "00:11:22:33:44:55"
        with patch("scanner_service.srp", return_value=([(None, received)], [])), \
             patch("scanner_service._build_device", return_value=MagicMock(ip="192.168.1.10")):
            from scanner_service import scan_network
            assert len(scan_network("192.168.1.0/24", mdns_timeout=0)) == 1

    def test_skips_devices_when_build_device_returns_none(self):
        received = MagicMock()
        received.psrc = "192.168.1.1"
        received.hwsrc = "00:11:22:33:44:55"
        with patch("scanner_service.srp", return_value=([(None, received)], [])), \
             patch("scanner_service._build_device", return_value=None):
            from scanner_service import scan_network
            assert scan_network("192.168.1.0/24", mdns_timeout=0) == []

