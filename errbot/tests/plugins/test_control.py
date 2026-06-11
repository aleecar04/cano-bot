import json
from unittest.mock import MagicMock, patch

from plugins.control.control import Control, _patch_device_status


def _make_control():
    ctrl = Control.__new__(Control)
    ctrl.log = MagicMock()
    return ctrl


class TestControlPlugin:

    def test_patch_device_status_skips_when_unreachable(self):
        with patch("plugins.control.control.is_backend_reachable", return_value=False), \
             patch("plugins.control.control.api_devices.patch_status") as mock_patch:
            _patch_device_status("device_lampara", True, {"power": "on"})
        mock_patch.assert_not_called()

    def test_patch_device_status_calls_api_when_reachable(self):
        with patch("plugins.control.control.is_backend_reachable", return_value=True), \
             patch("plugins.control.control.api_devices.patch_status") as mock_patch:
            _patch_device_status("device_lampara", True, {"power": "on"})
        mock_patch.assert_called_once_with("device_lampara", True, {"power": "on"}, timeout=5)

    def test_control_device_invalid_json_returns_error(self):
        result = _make_control().control_device(MagicMock(frm="anabel@xmpp.cano-app.com"), "not-json")
        assert result["ok"] is False

    def test_control_device_unknown_device_returns_error(self):
        args = json.dumps({"device_id": "no-existe", "action": "encender", "payload": {}})
        with patch("plugins.control.control.get_device", return_value=None):
            result = _make_control().control_device(MagicMock(frm="anabel@xmpp.cano-app.com"), args)
        assert result["ok"] is False and "no encontrado" in result["error"].lower()

    def test_control_device_returns_driver_result(self):
        args = json.dumps({"device_id": "device_lampara", "action": "encender", "payload": {}})
        device = {"id": "device_lampara", "type": "Luz", "driver": "tuya", "name": "Lampara Salon"}
        with patch("plugins.control.control.get_device", return_value=device), \
             patch("plugins.control.control.execute_command", return_value={"ok": True}), \
             patch("plugins.control.control._patch_device_status"):
            assert _make_control().control_device(MagicMock(frm="anabel@xmpp.cano-app.com"), args)["ok"] is True

    def test_list_devices_returns_serialized_list_or_error(self):
        ctrl = _make_control()
        msg = MagicMock(frm="anabel@xmpp.cano-app.com")
        devices = [
            {"id": "device_lampara", "name": "Lampara Salon", "type": "Luz", "driver": "tuya",
             "is_online": True, "state": {"power": "on"}},
            {"id": "device_tv", "name": "TV", "type": "SmartTV", "driver": "lg_tv",
             "is_online": False, "state": {}},
        ]
        with patch("plugins.control.control.api_devices.get_all", return_value=devices):
            result = ctrl.list_devices(msg, "")
        assert result["tipo"] == "device_list" and result["total"] == 2
        assert result["dispositivos"][0]["id"] == "device_lampara"

        with patch("plugins.control.control.api_devices.get_all", side_effect=RuntimeError("boom")):
            result = ctrl.list_devices(msg, "")
        assert result["tipo"] == "error" and "boom" in result["mensaje"]
