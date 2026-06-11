from unittest.mock import MagicMock

import pytest

from drivers.base import BaseDriver


def _make_concrete():
    class Concrete(BaseDriver):
        def get_status(self, device, timeout=2.0):
            return {"is_online": True}
        def turn_on(self, device):
            return {"ok": True}
        def turn_off(self, device):
            return {"ok": True}
    return Concrete()


class TestBaseDriver:

    @pytest.mark.parametrize("method_name, args", [
        ("brightness", ({}, 50)),
        ("set_volume", ({}, 50)),
    ])
    def test_optional_actions_return_not_supported_by_default(self, method_name, args):
        assert getattr(_make_concrete(), method_name)(*args)["ok"] is False

    @pytest.mark.parametrize("payload, expected_rgb", [
        ({"color": "rojo"}, (255, 0, 0)),
        ({"r": 100, "g": 200, "b": 50}, (100, 200, 50)),
    ])
    def test_dispatch_color_maps_name_or_explicit_rgb(self, payload, expected_rgb):
        drv = _make_concrete()
        drv.set_color_rgb = MagicMock(return_value={"ok": True})
        drv._dispatch_color({}, payload)
        assert drv.set_color_rgb.call_args[0][1:] == expected_rgb

    def test_error_for_unknown_color(self):
        result = _make_concrete()._dispatch_color({}, {"color": "salmon"})
        assert result["ok"] is False and "salmon" in result["error"].lower()

    def test_rejects_unknown_actions(self):
        assert _make_concrete().execute({}, "accion_inventada", {})["ok"] is False

    def test_execute_propagates_and_wraps_exceptions(self):
        drv = _make_concrete()
        drv.turn_on = MagicMock(return_value={"ok": True, "marker": "enc"})
        assert drv.execute({}, "encender", {})["marker"] == "enc"

        drv.turn_on = MagicMock(side_effect=RuntimeError("boom"))
        result = drv.execute({}, "encender", {})
        assert result["ok"] is False and "boom" in result["error"]
