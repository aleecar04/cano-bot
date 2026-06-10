import json
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).parent.parent.parent.parent
extra_plugin_dir = str(ROOT / "plugins" / "network-scanner")


def _get_plugin(testbot):
    return testbot.bot.plugin_manager.get_plugin_obj_by_name("Scanner")


def _fake_device(ip="192.168.1.10", tipo="Luz"):
    from scanner_service import DeviceInfo
    return DeviceInfo(ip=ip, mac="aa:bb:cc:dd:ee:ff", hostname="fake-device", tipo=tipo)


def _parse(result):
    return result if isinstance(result, dict) else json.loads(result)


class TestScanDevicesPlugin:
    extra_plugin_dir = str(ROOT / "plugins" / "network-scanner")

    def test_scan_with_auto_network_returns_response(self, testbot, monkeypatch):
        plugin = _get_plugin(testbot)
        g = plugin.scan_devices.__globals__
        monkeypatch.setitem(g, "get_local_network", lambda: ("192.168.1.1", "192.168.1.0/24"))
        monkeypatch.setitem(g, "scan_network", lambda network: [_fake_device(), _fake_device("192.168.1.11", "SmartTV")])
        data = _parse(plugin.scan_devices(MagicMock(), ""))
        assert data["tipo"] == "scan_response"
        assert data["total"] == 2 and data["red"] == "192.168.1.0/24"

    def test_scan_with_explicit_network_arg(self, testbot, monkeypatch):
        plugin = _get_plugin(testbot)
        monkeypatch.setitem(plugin.scan_devices.__globals__, "scan_network", lambda network: [_fake_device()])
        data = _parse(plugin.scan_devices(MagicMock(), "10.0.0.0/24"))
        assert data["red"] == "10.0.0.0/24" and data["ip_bot"] is None

    def test_scan_returns_error_when_no_network_detected(self, testbot, monkeypatch):
        plugin = _get_plugin(testbot)
        monkeypatch.setitem(plugin.scan_devices.__globals__, "get_local_network", lambda: (None, None))
        assert _parse(plugin.scan_devices(MagicMock(), ""))["tipo"] == "error"

    def test_scan_returns_error_with_message_when_exception(self, testbot, monkeypatch):
        def raise_error():
            raise RuntimeError("adapter down")
        plugin = _get_plugin(testbot)
        monkeypatch.setitem(plugin.scan_devices.__globals__, "get_local_network", raise_error)
        data = _parse(plugin.scan_devices(MagicMock(), ""))
        assert data["tipo"] == "error" and "adapter down" in data["mensaje"]

