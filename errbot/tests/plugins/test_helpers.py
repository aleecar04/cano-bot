from unittest.mock import patch

import pytest

from plugins._helpers import calculate_expected_state, find_device_by_name, _normalize_text


_DEVICES = [{"id": "1", "name": "Tele Salón"}, {"id": "2", "name": "Luz Cocina"}]


class TestFindDeviceByName:

    @pytest.mark.parametrize("query, expected_id", [
        ("Tele Salón", "1"),      
        ("tele", "1"),              
        ("TELE SALON", "1"),        
        ("tele del salón", "1"), 
        ("cocina", "2"),           
        ("nevera", None),           
        ("", None),                
    ])
    def test_find_device_by_name_is_fuzzy(self, query, expected_id):
        with patch("plugins._helpers.api_devices.get_all", return_value=_DEVICES):
            result = find_device_by_name(query)
        assert (result["id"] if result else None) == expected_id

    def test_find_device_by_name_no_devices(self):
        with patch("plugins._helpers.api_devices.get_all", return_value=[]):
            assert find_device_by_name("tele") is None

    def test_normalize_text_strips_accents_case_and_spaces(self):
        assert _normalize_text("  Tele   SALÓN ") == "tele salon"


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
