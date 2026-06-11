from unittest.mock import MagicMock, patch

import pytest

from scanner import Scanner
from scanner_service import DeviceInfo


def _make_scanner():
    s = Scanner.__new__(Scanner)
    s.log = MagicMock()
    return s


def _device(ip="192.168.1.10", tipo="Luz"):
    return DeviceInfo(ip=ip, mac="aa:bb:cc:dd:ee:ff", hostname="fake-device", tipo=tipo)


class TestScannerPlugin:

    @pytest.mark.parametrize("args, expected_red, expected_ip", [
        ("",            "192.168.1.0/24", "192.168.1.1"),
        ("10.0.0.0/24", "10.0.0.0/24",    None),
    ])
    def test_scan_devices_uses_detected_or_arg_network(self, args, expected_red, expected_ip):
        with patch("scanner.get_local_network", return_value=("192.168.1.1", "192.168.1.0/24")), \
             patch("scanner.scan_network", return_value=[_device(), _device("192.168.1.11", "SmartTV")]):
            data = _make_scanner().scan_devices(MagicMock(), args)
        assert data["tipo"] == "scan_response"
        assert data["red"] == expected_red and data["ip_bot"] == expected_ip

    def test_scan_devices_error_if_no_network(self):
        with patch("scanner.get_local_network", return_value=(None, None)):
            data = _make_scanner().scan_devices(MagicMock(), "")
        assert data["tipo"] == "error"

    def test_scan_devices_translates_exception_to_error(self):
        with patch("scanner.get_local_network", side_effect=RuntimeError("adapter down")):
            data = _make_scanner().scan_devices(MagicMock(), "")
        assert data["tipo"] == "error" and "adapter down" in data["mensaje"]
