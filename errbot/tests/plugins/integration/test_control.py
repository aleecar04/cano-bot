import ast
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).parent.parent.parent.parent
extra_plugin_dir = str(ROOT / "plugins" / "control")


DEVICE_LUZ = {
    "id": "dev-luz", "name": "Luz Salón", "type": "Luz", "driver": "tuya",
    "is_online": True, "estado": {"power": "off"},
}
DEVICE_TV = {
    "id": "dev-tv", "name": "Televisión", "type": "SmartTV", "driver": "lgtv",
    "is_online": True, "estado": {"power": "off", "volume": 30},
}
ALL_DEVICES = [DEVICE_LUZ, DEVICE_TV]


def _make_response(data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


def _get_router(devices=ALL_DEVICES):
    def _impl(url, **kwargs):
        if "/users/resolve" in url:
            return _make_response({"user_id": "uid-test"})
        if "/devices/all" in url:
            return _make_response(devices)
        return _make_response({}, 200)
    return _impl


def _ok_post_patch(url, **kwargs):
    return _make_response({}, 200)


def _parse(msg):
    if isinstance(msg, dict):
        return msg
    try:
        return json.loads(msg)
    except (json.JSONDecodeError, TypeError):
        return ast.literal_eval(msg)


class TestListDevices:
    extra_plugin_dir = str(ROOT / "plugins" / "control")

    def test_returns_device_list_with_names_and_count(self, testbot):
        with patch("requests.get",   side_effect=_get_router()), \
             patch("requests.patch", side_effect=_ok_post_patch), \
             patch("requests.post",  side_effect=_ok_post_patch):
            testbot.push_message("!list_devices")
            data = _parse(testbot.pop_message())
        names = [d["name"] for d in data["dispositivos"]]
        assert data["tipo"] == "device_list" and data["total"] == 2
        assert "Luz Salón" in names and "Televisión" in names

    def test_returns_empty_list_when_no_devices(self, testbot):
        with patch("requests.get",   side_effect=_get_router(devices=[])), \
             patch("requests.patch", side_effect=_ok_post_patch), \
             patch("requests.post",  side_effect=_ok_post_patch):
            testbot.push_message("!list_devices")
            data = _parse(testbot.pop_message())
        assert data["total"] == 0


class TestControlDevice:
    extra_plugin_dir = str(ROOT / "plugins" / "control")

    def _exec(self, testbot, device_id, action, payload=None, driver_ok=True):
        driver_result = {"ok": True} if driver_ok else {"ok": False, "error": "timeout"}
        args_dict = {"device_id": device_id, "action": action}
        if payload:
            args_dict["payload"] = payload
        control_mod = sys.modules.get("errbot.plugins.control")
        ejecutar_patch = (
            patch.object(control_mod, "ejecutar_comando", return_value=driver_result)
            if control_mod else patch("builtins.id")
        )
        with ejecutar_patch, \
             patch("requests.get",   side_effect=_get_router()), \
             patch("requests.patch", side_effect=_ok_post_patch), \
             patch("requests.post",  side_effect=_ok_post_patch):
            testbot.push_message(f"!control_device {json.dumps(args_dict)}")
            return _parse(testbot.pop_message())

    @pytest.mark.parametrize("device_id, action, payload", [
        ("dev-luz", "encender", None),
        ("dev-luz", "brillo", {"valor": 75}),
    ])
    def test_known_actions_return_ok(self, testbot, device_id, action, payload):
        assert self._exec(testbot, device_id, action, payload=payload)["ok"] is True

    def test_unknown_device_returns_error(self, testbot):
        result = self._exec(testbot, "ghost-id", "encender")
        assert result["ok"] is False and "no encontrado" in result["error"].lower()

    def test_driver_failure_returns_ok_false(self, testbot):
        assert self._exec(testbot, "dev-luz", "encender", driver_ok=False)["ok"] is False

    @pytest.mark.parametrize("args", ["not-valid-json", "{}"])
    def test_invalid_args_return_error(self, testbot, args):
        testbot.push_message(f"!control_device {args}")
        assert _parse(testbot.pop_message())["ok"] is False
