import json
from unittest.mock import MagicMock, patch


def _make_control():
    from plugins.control.control import Control
    ctrl = Control.__new__(Control)
    ctrl.log = MagicMock()
    return ctrl


class TestPatchDeviceStatus:

    def test_skips_call_when_backend_unreachable(self):
        from plugins.control.control import _patch_device_status
        with patch("plugins.control.control.is_backend_reachable", return_value=False), \
             patch("plugins.control.control.api_devices.patch_status") as mock_patch:
            _patch_device_status("d1", True, {"power": "on"})
        mock_patch.assert_not_called()

    def test_calls_api_with_timeout_when_reachable(self):
        from plugins.control.control import _patch_device_status
        with patch("plugins.control.control.is_backend_reachable", return_value=True), \
             patch("plugins.control.control.api_devices.patch_status") as mock_patch:
            _patch_device_status("d1", True, {"power": "on"})
        mock_patch.assert_called_once_with("d1", True, {"power": "on"}, timeout=5)

class TestControlDevice:

    def test_invalid_json_returns_error(self):
        result = _make_control().control_device(MagicMock(frm="alice@x"), "not-json")
        assert result["ok"] is False

    def test_unknown_device_returns_error(self):
        args = json.dumps({"device_id": "no-existe", "action": "encender", "payload": {}})
        with patch("plugins.control.control.get_device", return_value=None):
            result = _make_control().control_device(MagicMock(frm="alice@x"), args)
        assert result["ok"] is False and "no encontrado" in result["error"].lower()

    def test_happy_path_returns_driver_result(self):
        args = json.dumps({"device_id": "d1", "action": "encender", "payload": {}})
        device = {"id": "d1", "type": "Luz", "driver": "tuya", "name": "Luz"}
        with patch("plugins.control.control.get_device", return_value=device), \
             patch("plugins.control.control.ejecutar_comando", return_value={"ok": True}), \
             patch("plugins.control.control._patch_device_status"):
            assert _make_control().control_device(MagicMock(frm="alice@x"), args)["ok"] is True

def test_list_devices_returns_serialized_list_or_error():
    ctrl = _make_control()
    msg = MagicMock(frm="alice@x")
    devices = [
        {"id": "d1", "name": "Luz", "type": "Luz", "driver": "tuya",
         "is_online": True, "estado": {"power": "on"}},
        {"id": "d2", "name": "TV", "type": "SmartTV", "driver": "lg_tv",
         "is_online": False, "estado": {}},
    ]
    with patch("plugins.control.control.api_devices.get_all", return_value=devices):
        result = ctrl.list_devices(msg, "")
    assert result["tipo"] == "device_list" and result["total"] == 2
    assert result["dispositivos"][0]["id"] == "d1"

    with patch("plugins.control.control.api_devices.get_all", side_effect=RuntimeError("boom")):
        result = ctrl.list_devices(msg, "")
    assert result["tipo"] == "error" and "boom" in result["mensaje"]


