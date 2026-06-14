import pytest

from plugins._helpers import calculate_expected_state


class TestHelpers:

    @pytest.mark.parametrize("device, action, expected_power", [
        ({}, "encender", "on"),
        ({"power": "on"}, "apagar", "off"),
    ])
    def test_power_actions_toggle_state(self, device, action, expected_power):
        assert calculate_expected_state(device, action, {})["power"] == expected_power

    @pytest.mark.parametrize("device, action, payload, expected_volume", [
        ({"state": {"volume": 98}}, "subir_volumen", {},             100),
        ({"state": {"volume": 2}},  "bajar_volumen", {},             0),
        ({"state": {"volume": 70}}, "mute",          {},             0),
        ({},                          "set_volumen",   {"value": 35},  35),
        ({},                          "set_volumen",   {"value": 200}, 100),
    ])
    def test_volume_actions_step_and_clamp(self, device, action, payload, expected_volume):
        assert calculate_expected_state(device, action, payload)["volume"] == expected_volume

    def test_color_rgb_sets_hex_only_for_known_color_names(self):
        result = calculate_expected_state({}, "color_rgb", {"color": "azul"})
        assert result["color_hex"] == "#0000ff" and result["work_mode"] == "colour"

        result = calculate_expected_state({}, "color_rgb", {"color": "salmon"})
        assert "color_hex" not in result and result["work_mode"] == "colour"

    def test_unknown_action_returns_unchanged_and_pure(self):
        estado = {"power": "on", "brightness": 50}
        assert calculate_expected_state({"state": estado}, "desconocida", {}) == estado

        original = {"power": "off"}
        calculate_expected_state({"state": original}, "encender", {})
        assert original["power"] == "off"
