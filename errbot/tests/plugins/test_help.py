from unittest.mock import MagicMock, patch

import pytest

from drivers.actions_catalog import Action
from plugins.help.help import Help, _format_actions_for_device, get_supported_actions


def _make_help():
    h = Help.__new__(Help)
    h.log = MagicMock()
    return h


class TestHelpPlugin:

    @pytest.mark.parametrize("device_type, must_include, must_exclude", [
        ("Enchufe", ["ENCENDER"], ["BRILLO"]),
        ("light", ["BRILLO"], []),
    ])
    def test_get_supported_actions_for_known_types(self, device_type, must_include, must_exclude):
        actions = get_supported_actions(device_type)
        for name in must_include:
            assert getattr(Action, name) in actions
        for name in must_exclude:
            assert getattr(Action, name) not in actions

    def test_get_supported_actions_empty_for_unknown(self):
        assert get_supported_actions("Robot Aspirador") == set()

    def test_format_actions_for_device(self):
        result = _format_actions_for_device({"name": "Lampara Salon", "type": "Luz"})
        assert "Lampara Salon" in result and "Luz / Bombilla" in result and "encender" in result

    def test_acciones_for_device(self):
        device = {"id": "device_lampara", "name": "Lampara Salon", "type": "Luz"}
        with patch("plugins.help.help.find_device_by_name", return_value=device):
            result = _make_help().acciones(MagicMock(frm="anabel@xmpp.cano-app.com"), "lampara salon")
        assert "Lampara Salon" in result and "encender" in result

    def test_acciones_for_missing_device_returns_error(self):
        with patch("plugins.help.help.find_device_by_name", return_value=None):
            result = _make_help().acciones(MagicMock(frm="anabel@xmpp.cano-app.com"), "fantasma")
        assert "No he encontrado" in result and "fantasma" in result
