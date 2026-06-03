import socket
from unittest.mock import MagicMock, patch


# ── is_mac_randomized / get_vendor ───────────────────────────────────────────

class TestIsMacRandomized:

    def test_mac_locally_administered_es_random(self):
        from scanner_service import is_mac_randomized
        # 0x02 set en el primer byte → locally administered
        assert is_mac_randomized("02:11:22:33:44:55") is True
        assert is_mac_randomized("06:aa:bb:cc:dd:ee") is True

    def test_mac_universal_no_es_random(self):
        from scanner_service import is_mac_randomized
        assert is_mac_randomized("00:11:22:33:44:55") is False
        assert is_mac_randomized("8c:ae:4c:11:22:33") is False

    def test_mac_invalida_devuelve_false(self):
        from scanner_service import is_mac_randomized
        assert is_mac_randomized("no-es-mac") is False
        assert is_mac_randomized("") is False


class TestGetVendor:

    def test_mac_random_devuelve_none(self):
        from scanner_service import get_vendor
        assert get_vendor("02:11:22:33:44:55") is None

    def test_mac_normal_consulta_oui(self):
        import scanner_service
        with patch.object(scanner_service._MAC_LOOKUP, "lookup", return_value="Apple, Inc."), \
             patch("scanner_service._ensure_mac_vendors_loaded"):
            assert scanner_service.get_vendor("00:11:22:33:44:55") == "Apple, Inc."

    def test_lookup_excepcion_devuelve_none(self):
        import scanner_service
        with patch.object(scanner_service._MAC_LOOKUP, "lookup", side_effect=KeyError("no")), \
             patch("scanner_service._ensure_mac_vendors_loaded"):
            assert scanner_service.get_vendor("00:11:22:33:44:55") is None


class TestEnsureMacVendorsLoaded:

    def test_actualiza_la_primera_vez(self):
        import scanner_service
        scanner_service._MAC_VENDORS_UPDATED = False
        with patch.object(scanner_service._MAC_LOOKUP, "update_vendors") as mock_u:
            scanner_service._ensure_mac_vendors_loaded()
        mock_u.assert_called_once()
        assert scanner_service._MAC_VENDORS_UPDATED is True

    def test_no_actualiza_la_segunda_vez(self):
        import scanner_service
        scanner_service._MAC_VENDORS_UPDATED = True
        with patch.object(scanner_service._MAC_LOOKUP, "update_vendors") as mock_u:
            scanner_service._ensure_mac_vendors_loaded()
        mock_u.assert_not_called()

    def test_silencia_excepcion_sin_red(self):
        import scanner_service
        scanner_service._MAC_VENDORS_UPDATED = False
        with patch.object(scanner_service._MAC_LOOKUP, "update_vendors",
                          side_effect=RuntimeError("no internet")):
            scanner_service._ensure_mac_vendors_loaded()
        assert scanner_service._MAC_VENDORS_UPDATED is True


# ── _match_pattern / _match_mdns ─────────────────────────────────────────────

class TestMatchPattern:

    def test_value_vacio_no_suma(self):
        from scanner_service import _match_pattern
        scores: dict = {}
        _match_pattern("", {"Luz": ["hue"]}, 3, scores)
        assert scores == {}

    def test_keyword_substring_suma_peso(self):
        from scanner_service import _match_pattern
        scores: dict = {}
        _match_pattern("Hue-Bridge", {"Luz": ["hue"], "TV": ["samsung"]}, 3, scores)
        assert scores == {"Luz": 3}

    def test_match_es_case_insensitive(self):
        from scanner_service import _match_pattern
        scores: dict = {}
        _match_pattern("PHILIPS-LIGHT-1", {"Luz": ["philips"]}, 3, scores)
        assert scores == {"Luz": 3}

    def test_solo_primer_match(self):
        from scanner_service import _match_pattern
        scores: dict = {}
        _match_pattern("hue-and-samsung", {"Luz": ["hue"], "TV": ["samsung"]}, 3, scores)
        # Solo el primer tipo que matchea (orden del dict)
        assert sum(scores.values()) == 3


class TestMatchMdns:

    def test_servicio_conocido_suma_peso(self):
        from scanner_service import _match_mdns, _WEIGHT_MDNS
        scores: dict = {}
        _match_mdns(["_hue._tcp.local."], scores)
        assert scores["Luz"] == _WEIGHT_MDNS

    def test_servicio_desconocido_no_suma(self):
        from scanner_service import _match_mdns
        scores: dict = {}
        _match_mdns(["_inventado._tcp.local."], scores)
        assert scores == {}

    def test_varios_servicios_suman(self):
        from scanner_service import _match_mdns
        scores: dict = {}
        _match_mdns(["_hue._tcp.local.", "_googlecast._tcp.local."], scores)
        assert "Luz" in scores
        assert "SmartTV" in scores


# ── detect_device_type ───────────────────────────────────────────────────────

class TestDetectDeviceType:

    def test_sin_pistas_devuelve_dispositivo_generico(self):
        from scanner_service import detect_device_type
        assert detect_device_type(None, None, []) == "Dispositivo"

    def test_hostname_solo_clasifica(self):
        from scanner_service import detect_device_type
        assert detect_device_type("hue-bridge", None, []) == "Luz"

    def test_vendor_gana_a_hostname(self):
        """Vendor pesa más (3) que hostname (1)."""
        from scanner_service import detect_device_type
        # hostname dice "esp" (IoT), vendor dice "samsung" (SmartTV)
        result = detect_device_type("esp-1", "samsung electronics", [])
        assert result == "SmartTV"

    def test_mdns_gana_a_vendor(self):
        """mDNS pesa más (4) que vendor (3)."""
        from scanner_service import detect_device_type
        result = detect_device_type(None, "samsung", ["_hue._tcp.local."])
        assert result == "Luz"


# ── _MdnsCollector ───────────────────────────────────────────────────────────

class TestMdnsCollector:

    def test_add_service_indexa_por_ip(self):
        from scanner_service import _MdnsCollector
        c = _MdnsCollector()
        zc = MagicMock()
        info = MagicMock()
        info.addresses = [socket.inet_aton("192.168.1.10")]
        zc.get_service_info.return_value = info
        c.add_service(zc, "_hue._tcp.local.", "name")
        assert c.results == {"192.168.1.10": ["_hue._tcp.local."]}

    def test_add_service_sin_info_silencia(self):
        from scanner_service import _MdnsCollector
        c = _MdnsCollector()
        zc = MagicMock()
        zc.get_service_info.return_value = None
        c.add_service(zc, "_hue._tcp.local.", "name")
        assert c.results == {}

    def test_remove_service_no_lanza(self):
        from scanner_service import _MdnsCollector
        c = _MdnsCollector()
        c.remove_service(MagicMock(), "type", "name")  # no-op

    def test_update_service_no_lanza(self):
        from scanner_service import _MdnsCollector
        c = _MdnsCollector()
        c.update_service(MagicMock(), "type", "name")  # no-op

    def test_add_service_no_duplica(self):
        from scanner_service import _MdnsCollector
        c = _MdnsCollector()
        zc = MagicMock()
        info = MagicMock()
        info.addresses = [socket.inet_aton("192.168.1.10")]
        zc.get_service_info.return_value = info
        c.add_service(zc, "_hue._tcp.local.", "name")
        c.add_service(zc, "_hue._tcp.local.", "name")
        assert c.results["192.168.1.10"] == ["_hue._tcp.local."]


# ── get_local_network ────────────────────────────────────────────────────────

class TestGetLocalNetwork:

    def test_descarta_loopback(self):
        with patch("scanner_service.netifaces.interfaces", return_value=["lo"]), \
             patch("scanner_service.netifaces.ifaddresses",
                   return_value={2: [{"addr": "127.0.0.1", "netmask": "255.0.0.0"}]}):
            from scanner_service import get_local_network
            assert get_local_network() == (None, None)

    def test_devuelve_red_valida(self):
        import scanner_service
        with patch.object(scanner_service.netifaces, "interfaces", return_value=["eth0"]), \
             patch.object(scanner_service.netifaces, "ifaddresses",
                          return_value={scanner_service.netifaces.AF_INET: [
                              {"addr": "192.168.1.50", "netmask": "255.255.255.0"}
                          ]}):
            from scanner_service import get_local_network
            ip, net = get_local_network()
        assert ip == "192.168.1.50"
        assert "192.168.1.0/24" in net

    def test_excepcion_devuelve_none_none(self):
        with patch("scanner_service.netifaces.interfaces", side_effect=RuntimeError("boom")):
            from scanner_service import get_local_network
            assert get_local_network() == (None, None)


# ── _resolve_hostname ────────────────────────────────────────────────────────

class TestResolveHostname:

    def test_hostname_resuelto_devuelve_nombre(self):
        with patch("scanner_service.socket.gethostbyaddr",
                   return_value=("my-host.local", [], [])):
            from scanner_service import _resolve_hostname
            assert _resolve_hostname("192.168.1.10") == "my-host.local"

    def test_excepcion_devuelve_none(self):
        with patch("scanner_service.socket.gethostbyaddr",
                   side_effect=OSError("not found")):
            from scanner_service import _resolve_hostname
            assert _resolve_hostname("192.168.1.10") is None


# ── _build_device ────────────────────────────────────────────────────────────

class TestBuildDevice:

    def test_router_se_descarta(self):
        with patch("scanner_service._resolve_hostname", return_value="router-1"), \
             patch("scanner_service.get_vendor", return_value="Cisco Systems"):
            from scanner_service import _build_device
            assert _build_device("192.168.1.1", "00:11:22:33:44:55", {}) is None

    def test_construye_device_con_clasificacion(self):
        with patch("scanner_service._resolve_hostname", return_value="hue-bridge"), \
             patch("scanner_service.get_vendor", return_value="Signify"):
            from scanner_service import _build_device
            dev = _build_device("192.168.1.10", "00:11:22:33:44:55", {})
        assert dev is not None
        assert dev.ip == "192.168.1.10"
        assert dev.tipo == "Luz"

    def test_sin_hostname_usa_ip(self):
        with patch("scanner_service._resolve_hostname", return_value=None), \
             patch("scanner_service.get_vendor", return_value=None):
            from scanner_service import _build_device
            dev = _build_device("192.168.1.10", "00:11:22:33:44:55", {})
        assert dev.hostname == "192.168.1.10"


# ── scan_network ─────────────────────────────────────────────────────────────

class TestScanNetwork:

    def test_arp_fallo_devuelve_lista_vacia(self):
        with patch("scanner_service.srp", side_effect=RuntimeError("no privs")):
            from scanner_service import scan_network
            assert scan_network("192.168.1.0/24", mdns_timeout=0) == []

    def test_sin_hosts_devuelve_vacio(self):
        with patch("scanner_service.srp", return_value=([], [])):
            from scanner_service import scan_network
            assert scan_network("192.168.1.0/24", mdns_timeout=0) == []

    def test_con_hosts_construye_devices(self):
        # Mock de scapy: lista de tuplas (_, received) con .psrc y .hwsrc
        received = MagicMock()
        received.psrc = "192.168.1.10"
        received.hwsrc = "00:11:22:33:44:55"
        with patch("scanner_service.srp", return_value=([(None, received)], [])), \
             patch("scanner_service._build_device") as mock_build:
            mock_build.return_value = MagicMock(ip="192.168.1.10")
            from scanner_service import scan_network
            devices = scan_network("192.168.1.0/24", mdns_timeout=0)
        assert len(devices) == 1
        mock_build.assert_called_once()

    def test_build_device_devuelve_none_se_descarta(self):
        received = MagicMock()
        received.psrc = "192.168.1.1"
        received.hwsrc = "00:11:22:33:44:55"
        with patch("scanner_service.srp", return_value=([(None, received)], [])), \
             patch("scanner_service._build_device", return_value=None):
            from scanner_service import scan_network
            assert scan_network("192.168.1.0/24", mdns_timeout=0) == []

    def test_build_device_excepcion_se_loggea_y_sigue(self):
        received = MagicMock()
        received.psrc = "192.168.1.10"
        received.hwsrc = "00:11:22:33:44:55"
        with patch("scanner_service.srp", return_value=([(None, received)], [])), \
             patch("scanner_service._build_device", side_effect=RuntimeError("boom")):
            from scanner_service import scan_network
            assert scan_network("192.168.1.0/24", mdns_timeout=0) == []
