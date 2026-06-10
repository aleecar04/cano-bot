import pytest

from app.services.device_catalog import Action, is_action_supported, validate_payload


@pytest.mark.parametrize("device_type, action, supported", [
    ("Luz", "brillo", True),
    ("Enchufe", "encender", True),
    ("Enchufe", "brillo", False),
    ("SmartTV", "set_volumen", True),
    ("SmartTV", "abrir_app", True),
    ("light", "brillo", True),
    ("switch", "encender", True),
    ("media_player", "subir_volumen", True),
    ("OnirixDevice", "encender", False),
    ("Luz", "telepatear", False),
])
def test_is_action_supported_per_device_category(device_type, action, supported):
    assert is_action_supported(device_type, action) is supported


@pytest.mark.parametrize("action, payload, ok", [
    ("temperatura_color", {"valor": 2700}, True),
    ("temperatura_color", {"valor": 3000}, False),
    ("temperatura_color", {}, False),
    ("color_rgb", {"color": "AZUL"}, True),
    ("color_rgb", {"color": "salmon"}, False),
    ("brillo", {"valor": 0}, True),
    ("brillo", {"valor": 100}, True),
    ("brillo", {"valor": 101}, False),
    ("brillo", {"valor": "abc"}, False),
    ("set_volumen", {"valor": 30}, True),
    ("set_volumen", {"valor": 200}, False),
    ("encender", {}, True),
    ("mute", {}, True),
])
def test_validate_payload_for_valid_or_invalid(action, payload, ok):
    result = validate_payload(action, payload)
    assert (result is None) is ok


def test_action_enum_values_are_lowercase_and_string_comparable():
    for a in Action:
        assert a.value.islower()
    assert Action.ENCENDER == "encender" and Action.COLOR_RGB == "color_rgb"
