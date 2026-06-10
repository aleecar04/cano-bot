from unittest.mock import patch

import pytest

from plugins._helpers import calculate_expected_state


@pytest.mark.parametrize("device, action, expected_power", [
    ({}, "encender", "on"),
    ({"power": "on"}, "apagar", "off"),
])
def test_power_actions_toggle_state(device, action, expected_power):
    assert calculate_expected_state(device, action, {})["power"] == expected_power


@pytest.mark.parametrize("device, action, expected_volume", [
    ({"estado": {"volume": 98}}, "subir_volumen", 100),
    ({"estado": {"volume": 2}}, "bajar_volumen", 0),
    ({}, "subir_volumen", 55),
])
def test_volume_steps_by_5_clamped_to_0_100_with_default_50(device, action, expected_volume):
    assert calculate_expected_state(device, action, {})["volume"] == expected_volume


def test_color_rgb_sets_hex_only_for_known_color_names():
    result = calculate_expected_state({}, "color_rgb", {"color": "azul"})
    assert result["color_hex"] == "#0000ff" and result["work_mode"] == "colour"

    result = calculate_expected_state({}, "color_rgb", {"color": "salmon"})
    assert "color_hex" not in result and result["work_mode"] == "colour"


def test_unknown_action_returns_unchanged_and_pure():
    estado = {"power": "on", "brightness": 50}
    assert calculate_expected_state({"estado": estado}, "desconocida", {}) == estado

    original = {"power": "off"}
    calculate_expected_state({"estado": original}, "encender", {})
    assert original["power"] == "off"


def _reset_cache():
    import plugins._helpers as h
    h._JID_CACHE.clear()


def test_resolve_sender_caches_after_first_call():
    _reset_cache()
    with patch("plugins._helpers.api_users.resolve_in_house", return_value="u1") as mock_api:
        from plugins._helpers import resolve_sender
        assert resolve_sender("alice@x/res") == "u1"
        resolve_sender("alice@x")
    mock_api.assert_called_once_with("alice@x")


def test_resolve_sender_refreshes_cache_after_ttl_expires():
    _reset_cache()
    import plugins._helpers as h
    with patch.object(h.api_users, "resolve_in_house", return_value="u1") as mock_api, \
         patch.object(h.time, "monotonic", side_effect=[100.0, 500.0, 500.0]):
        h.resolve_sender("alice@x")
        h.resolve_sender("alice@x")
    assert mock_api.call_count == 2


def test_find_device_by_name_matches_substring_case_insensitive():
    devices = [{"id": "d1", "name": "Luz Salón"}, {"id": "d2", "name": "TV Dormitorio"}]
    with patch("plugins._helpers.api_devices.get_all", return_value=devices):
        from plugins._helpers import find_device_by_name
        assert find_device_by_name("salón")["id"] == "d1"
