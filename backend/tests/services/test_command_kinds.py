import pytest

from app.services.command_kinds import (
    INFO_ACTIONS,
    PREFIX_ACTIONS,
    SYSTEM_ACTIONS,
    classify_action_type,
    lookup_prefix_command,
)


def test_classify_action_type_with_defaults():
    assert all(classify_action_type(a) == "info" for a in INFO_ACTIONS)
    assert all(classify_action_type(a) == "system" for a in SYSTEM_ACTIONS)
    assert classify_action_type("encender") == "device"
    assert classify_action_type(None) == "device"


@pytest.mark.parametrize("input_text, expected", [
    ("hola", None),
    ("", None),
    ("!", None),
    ("!inventado", None),
    ("!ayuda", {"intent": "ayuda"}),
    ("!scan_devices", {"intent": "scan_devices"}),
    ("!acciones", {"intent": "acciones"}),
    ("!acciones luz salon", {"intent": "acciones", "dispositivo": "luz salon"}),
])
def test_lookup_prefix_command(input_text, expected):
    assert lookup_prefix_command(input_text) == expected


def test_prefix_actions_is_union_of_info_and_system():
    assert PREFIX_ACTIONS == INFO_ACTIONS | SYSTEM_ACTIONS
