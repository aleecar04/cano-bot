"""
Integration tests for the Scanner errbot plugin.
Uses errbot's TestBot fixture; actual network scanning is mocked.

NOTE on patching:
  scanner.py does `from scanner_service import get_local_network, scan_network`,
  binding those names in the 'scanner' module's globals dict.
  We patch by modifying plugin.scan_devices.__globals__ directly via
  pytest's monkeypatch.setitem — this is guaranteed to reach the same
  namespace the method uses at call time.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).parent.parent.parent

extra_plugin_dir = str(ROOT / "plugins" / "network-scanner")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_plugin(testbot):
    return testbot.bot.plugin_manager.get_plugin_obj_by_name("Scanner")


def _fake_device(ip="192.168.1.10", tipo="Luz"):
    from scanner_service import DeviceInfo
    return DeviceInfo(
        ip=ip,
        mac="aa:bb:cc:dd:ee:ff",
        mac_aleatoria=False,
        hostname="fake-device",
        fabricante="FakeCo",
        tipo=tipo,
        confianza=3,
        puertos=[],
        mdns=[],
        deteccion={},
    )


# ── scan_devices ──────────────────────────────────────────────────────────────

class TestScanDevicesPlugin:
    extra_plugin_dir = str(ROOT / "plugins" / "network-scanner")

    def test_plugin_is_loaded(self, testbot):
        assert _get_plugin(testbot) is not None

    def test_scan_with_auto_network_returns_scan_response(self, testbot, monkeypatch):
        device = _fake_device()
        plugin = _get_plugin(testbot)
        g = plugin.scan_devices.__globals__
        monkeypatch.setitem(g, "get_local_network", lambda: ("192.168.1.1", "192.168.1.0/24"))
        monkeypatch.setitem(g, "scan_network", lambda network: [device])
        result = plugin.scan_devices(MagicMock(), "")
        data = json.loads(result)
        assert data["tipo"] == "scan_response"
        assert data["total"] == 1
        assert data["red"] == "192.168.1.0/24"

    def test_scan_with_explicit_network_arg(self, testbot, monkeypatch):
        device = _fake_device()
        plugin = _get_plugin(testbot)
        g = plugin.scan_devices.__globals__
        monkeypatch.setitem(g, "scan_network", lambda network: [device])
        result = plugin.scan_devices(MagicMock(), "10.0.0.0/24")
        data = json.loads(result)
        assert data["tipo"] == "scan_response"
        assert data["red"] == "10.0.0.0/24"
        assert data["ip_bot"] is None

    def test_scan_no_network_detected_returns_error(self, testbot, monkeypatch):
        plugin = _get_plugin(testbot)
        monkeypatch.setitem(plugin.scan_devices.__globals__, "get_local_network", lambda: (None, None))
        result = plugin.scan_devices(MagicMock(), "")
        data = json.loads(result)
        assert data["tipo"] == "error"

    def test_scan_exception_returns_error_json(self, testbot, monkeypatch):
        def raise_error():
            raise RuntimeError("adapter down")
        plugin = _get_plugin(testbot)
        monkeypatch.setitem(plugin.scan_devices.__globals__, "get_local_network", raise_error)
        result = plugin.scan_devices(MagicMock(), "")
        data = json.loads(result)
        assert data["tipo"] == "error"
        assert "adapter down" in data["mensaje"]

    def test_scan_empty_returns_zero_total(self, testbot, monkeypatch):
        plugin = _get_plugin(testbot)
        g = plugin.scan_devices.__globals__
        monkeypatch.setitem(g, "get_local_network", lambda: ("192.168.1.1", "192.168.1.0/24"))
        monkeypatch.setitem(g, "scan_network", lambda network: [])
        result = plugin.scan_devices(MagicMock(), "")
        data = json.loads(result)
        assert data["total"] == 0

    def test_scan_multiple_devices(self, testbot, monkeypatch):
        devices = [_fake_device("192.168.1.10", "Luz"), _fake_device("192.168.1.11", "SmartTV")]
        plugin = _get_plugin(testbot)
        g = plugin.scan_devices.__globals__
        monkeypatch.setitem(g, "get_local_network", lambda: ("192.168.1.1", "192.168.1.0/24"))
        monkeypatch.setitem(g, "scan_network", lambda network: devices)
        result = plugin.scan_devices(MagicMock(), "")
        data = json.loads(result)
        assert data["total"] == 2
