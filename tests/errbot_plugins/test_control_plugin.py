"""
Integration tests for the Control errbot plugin using errbot's TestBot fixture.

The testbot fixture (from errbot.backends.test) boots a real in-process bot
with the Test backend. Commands are sent via push_message / pop_message.
External HTTP calls are intercepted with unittest.mock.patch.
"""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# ── Plugin directory — read by the testbot pytest fixture ─────────────────────
ROOT = Path(__file__).parent.parent.parent
extra_plugin_dir = str(ROOT / "plugins" / "control")

# ── Fake data ─────────────────────────────────────────────────────────────────

DEVICE_LUZ = {
    "id": "dev-luz",
    "name": "Luz Salón",
    "type": "Luz",
    "driver": "tuya",
    "is_online": True,
    "estado": {"power": "off"},
}

DEVICE_TV = {
    "id": "dev-tv",
    "name": "Televisión",
    "type": "SmartTV",
    "driver": "lgtv",
    "is_online": True,
    "estado": {"power": "off", "volume": 30},
}

ALL_DEVICES = [DEVICE_LUZ, DEVICE_TV]


# ── Request mocks ──────────────────────────────────────────────────────────────

def _make_response(data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


def _get_router(url, **kwargs):
    if "/users/by-jid/" in url:
        return _make_response({"user_id": "uid-test"})
    if "/devices/all" in url:
        return _make_response(ALL_DEVICES)
    return _make_response({}, 200)  # /health etc.


def _patch_router(url, **kwargs):
    return _make_response({}, 200)


def _post_router(url, **kwargs):
    return _make_response({}, 200)




# ── list_devices ──────────────────────────────────────────────────────────────

class TestListDevices:
    extra_plugin_dir = str(ROOT / "plugins" / "control")

    def test_returns_device_list_json(self, testbot):
        with patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("!list_devices")
            msg = testbot.pop_message()

        data = json.loads(msg)
        assert data["tipo"] == "device_list"
        assert data["total"] == 2

    def test_includes_device_names(self, testbot):
        with patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("!list_devices")
            msg = testbot.pop_message()

        names = [d["name"] for d in json.loads(msg)["dispositivos"]]
        assert "Luz Salón" in names
        assert "Televisión" in names

    def test_empty_device_list(self, testbot):
        def no_devices(url, **kwargs):
            if "/users/by-jid/" in url:
                return _make_response({"user_id": "uid-test"})
            if "/devices/all" in url:
                return _make_response([])
            return _make_response({}, 200)

        with patch("requests.get",   side_effect=no_devices), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("!list_devices")
            msg = testbot.pop_message()

        assert json.loads(msg)["total"] == 0

    def test_includes_cache_summary(self, testbot):
        with patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("!list_devices")
            data = json.loads(testbot.pop_message())

        assert "cache_summary" in data


# ── control_device ────────────────────────────────────────────────────────────

class TestControlDevice:
    extra_plugin_dir = str(ROOT / "plugins" / "control")

    def _exec(self, testbot, device_id, accion, payload=None, driver_ok=True):
        """Helper: run !control_device and return parsed JSON result."""
        driver_result = {"ok": True} if driver_ok else {"ok": False, "error": "timeout"}
        args_dict = {"device_id": device_id, "accion": accion}
        if payload:
            args_dict["payload"] = payload
        import sys
        control_mod = sys.modules.get("errbot.plugins.control")
        patcher = patch.object(control_mod, "ejecutar_comando", return_value=driver_result) if control_mod else None
        ctx = patcher.__enter__() if patcher else None
        with patch("requests.get",   side_effect=_get_router), \
             patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message(f"!control_device {json.dumps(args_dict)}")
            return json.loads(testbot.pop_message())

    def test_encender_ok(self, testbot):
        result = self._exec(testbot, "dev-luz", "encender")
        assert result["ok"] is True

    def test_apagar_ok(self, testbot):
        result = self._exec(testbot, "dev-luz", "apagar")
        assert result["ok"] is True

    def test_subir_volumen_ok(self, testbot):
        result = self._exec(testbot, "dev-tv", "subir_volumen")
        assert result["ok"] is True

    def test_device_not_found_returns_error(self, testbot):
        result = self._exec(testbot, "ghost-id", "encender")
        assert result["ok"] is False
        assert "no encontrado" in result["error"].lower()

    def test_driver_failure_returns_ok_false(self, testbot):
        result = self._exec(testbot, "dev-luz", "encender", driver_ok=False)
        assert result["ok"] is False

    def test_invalid_json_args_returns_error(self, testbot):
        testbot.push_message("!control_device not-valid-json")
        result = json.loads(testbot.pop_message())
        assert result["ok"] is False

    def test_empty_args_returns_error(self, testbot):
        testbot.push_message("!control_device {}")
        result = json.loads(testbot.pop_message())
        assert result["ok"] is False

    def test_brillo_with_payload(self, testbot):
        result = self._exec(testbot, "dev-luz", "brillo", payload={"valor": 75})
        assert result["ok"] is True
