from unittest.mock import MagicMock

import pytest


def _make_concrete():
    from drivers.base import BaseDriver

    class Concrete(BaseDriver):
        def get_status(self, device, timeout=2.0):
            return {"is_online": True}
        def encender(self, device):
            return {"ok": True}
        def apagar(self, device):
            return {"ok": True}
    return Concrete()


@pytest.mark.parametrize("method_name, args", [
    ("brillo", ({}, 50)),
    ("set_volumen", ({}, 50)),
])
def test_optional_actions_return_not_supported_by_default(method_name, args):
    assert getattr(_make_concrete(), method_name)(*args)["ok"] is False


@pytest.mark.parametrize("payload, expected_rgb", [
    ({"color": "rojo"}, (255, 0, 0)),
    ({"r": 100, "g": 200, "b": 50}, (100, 200, 50))
])
def test_dispatch_color_maps_name_or_explicit_rgb(payload, expected_rgb):
    drv = _make_concrete()
    drv.color_rgb = MagicMock(return_value={"ok": True})
    drv._dispatch_color({}, payload)
    assert drv.color_rgb.call_args[0][1:] == expected_rgb


def test_dispatch_color_returns_error_for_unknown_color_name():
    result = _make_concrete()._dispatch_color({}, {"color": "salmon"})
    assert result["ok"] is False and "salmon" in result["error"].lower()


def test_ejecutar_rejects_unknown_actions():
    assert _make_concrete().ejecutar({}, "accion_inventada", {})["ok"] is False


@pytest.mark.parametrize("action, payload, method, expected_arg", [
    ("brillo", {"valor": 75}, "brillo", 75),
    ("abrir_app", {"app": "netflix"}, "abrir_app", "netflix"),
])
def test_ejecutar_passes_payload_value_to_method(action, payload, method, expected_arg):
    drv = _make_concrete()
    setattr(drv, method, MagicMock(return_value={"ok": True}))
    drv.ejecutar({}, action, payload)
    assert getattr(drv, method).call_args[0][1] == expected_arg


def test_ejecutar_propagates_and_wraps_exceptions():
    drv = _make_concrete()
    drv.encender = MagicMock(return_value={"ok": True, "marker": "enc"})
    assert drv.ejecutar({}, "encender", {})["marker"] == "enc"

    drv.encender = MagicMock(side_effect=RuntimeError("boom"))
    result = drv.ejecutar({}, "encender", {})
    assert result["ok"] is False and "boom" in result["error"]
