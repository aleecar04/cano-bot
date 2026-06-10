from unittest.mock import MagicMock, patch

import pytest


def _make_help():
    from plugins.help.help import Help
    h = Help.__new__(Help)
    h.log = MagicMock()
    return h


@pytest.mark.parametrize("device_type, must_include, must_exclude", [
    ("Enchufe", ["ENCENDER"], ["BRILLO"]),
    ("SmartTV", ["SET_VOLUMEN", "ABRIR_APP"], []),
    ("light", ["BRILLO"], []),
])
def test_get_supported_actions_returns_expected_for_known_types(device_type, must_include, must_exclude):
    from plugins.help.help import get_supported_actions
    from drivers.actions_catalog import Action
    actions = get_supported_actions(device_type)
    for name in must_include:
        assert getattr(Action, name) in actions
    for name in must_exclude:
        assert getattr(Action, name) not in actions


def test_get_supported_actions_returns_empty_for_unknown_type():
    from plugins.help.help import get_supported_actions
    assert get_supported_actions("AspiradoraRobot") == set()


def test_format_actions_for_device():
    from plugins.help.help import _format_actions_for_device
    result = _format_actions_for_device({"name": "Luz Salón", "type": "Luz"})
    assert "Luz Salón" in result and "Luz / Bombilla" in result and "encender" in result


class TestHelpPluginCommands:

    def test_ayuda_returns_help_text(self):
        from plugins.help.help import HELP_TEXT
        result = _make_help().ayuda(MagicMock(frm="alice@x"), "")
        assert result == HELP_TEXT

    def test_acciones_for_existing_device_returns_its_actions(self):
        device = {"id": "d1", "name": "Lámpara", "type": "Luz"}
        with patch("plugins.help.help.find_device_by_name", return_value=device):
            result = _make_help().acciones(MagicMock(frm="alice@x"), "lámpara")
        assert "Lámpara" in result and "encender" in result

    def test_acciones_for_missing_device_returns_error_with_query(self):
        with patch("plugins.help.help.find_device_by_name", return_value=None):
            result = _make_help().acciones(MagicMock(frm="alice@x"), "ghost")
        assert "No he encontrado" in result and "ghost" in result
