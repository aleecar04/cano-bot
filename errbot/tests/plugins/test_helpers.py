import pytest
from plugins._helpers import calculate_expected_state


# ── Power ─────────────────────────────────────────────────────────────────────

def test_encender_sets_power_on():
    result = calculate_expected_state({}, "encender", {})
    assert result["power"] == "on"


def test_apagar_sets_power_off():
    result = calculate_expected_state({"power": "on"}, "apagar", {})
    assert result["power"] == "off"


def test_encender_preserves_other_fields():
    # device["estado"] is the current state; encender must not wipe brightness
    device = {"estado": {"brightness": 80}}
    result = calculate_expected_state(device, "encender", {})
    assert result["power"] == "on"
    assert result["brightness"] == 80  # preserved from estado


def test_encender_preserves_existing_state_fields():
    # Pass state correctly nested under "estado"
    result = calculate_expected_state({"estado": {"power": "off", "brightness": 60}}, "encender", {})
    assert result["power"] == "on"
    assert result["brightness"] == 60


# ── Brightness ────────────────────────────────────────────────────────────────

def test_brillo_sets_brightness():
    result = calculate_expected_state({}, "brillo", {"valor": 75})
    assert result["brightness"] == 75


def test_brillo_uses_100_as_default():
    result = calculate_expected_state({}, "brillo", {})
    assert result["brightness"] == 100


# ── Volume ────────────────────────────────────────────────────────────────────

def test_subir_volumen_increases_by_5():
    result = calculate_expected_state({"estado": {"volume": 40}}, "subir_volumen", {})
    assert result["volume"] == 45


def test_bajar_volumen_decreases_by_5():
    result = calculate_expected_state({"estado": {"volume": 40}}, "bajar_volumen", {})
    assert result["volume"] == 35


def test_subir_volumen_caps_at_100():
    result = calculate_expected_state({"estado": {"volume": 98}}, "subir_volumen", {})
    assert result["volume"] == 100


def test_bajar_volumen_floors_at_0():
    result = calculate_expected_state({"estado": {"volume": 2}}, "bajar_volumen", {})
    assert result["volume"] == 0


def test_subir_volumen_starts_from_50_when_missing():
    result = calculate_expected_state({}, "subir_volumen", {})
    assert result["volume"] == 55


# ── Mute ─────────────────────────────────────────────────────────────────────

def test_mute_toggles_false_to_true():
    result = calculate_expected_state({"estado": {"muted": False}}, "mute", {})
    assert result["muted"] is True


def test_mute_toggles_true_to_false():
    result = calculate_expected_state({"estado": {"muted": True}}, "mute", {})
    assert result["muted"] is False


def test_mute_defaults_to_true_when_missing():
    result = calculate_expected_state({}, "mute", {})
    assert result["muted"] is True


# ── Unknown action ────────────────────────────────────────────────────────────

def test_unknown_action_returns_state_unchanged():
    estado = {"power": "on", "brightness": 50}
    result = calculate_expected_state({"estado": estado}, "desconocida", {})
    assert result == estado


def test_original_state_is_not_mutated():
    estado = {"power": "off"}
    device = {"estado": estado}
    calculate_expected_state(device, "encender", {})
    assert estado["power"] == "off"  # original estado dict must not be mutated


# ── resolve_sender (caché de 5 min) ──────────────────────────────────────────

import time as _time
from unittest.mock import patch as _patch


def _reset_cache():
    import plugins._helpers as h
    h._JID_CACHE.clear()


def test_resolve_sender_consulta_api_si_no_cacheado():
    _reset_cache()
    with _patch("plugins._helpers.api_users.resolve_in_house", return_value="u1") as mock_api:
        from plugins._helpers import resolve_sender
        assert resolve_sender("alice@x/res") == "u1"
    mock_api.assert_called_once_with("alice@x")


def test_resolve_sender_usa_cache_la_segunda_vez():
    _reset_cache()
    with _patch("plugins._helpers.api_users.resolve_in_house", return_value="u1") as mock_api:
        from plugins._helpers import resolve_sender
        resolve_sender("alice@x")
        resolve_sender("alice@x")
    mock_api.assert_called_once()  # solo la primera


def test_resolve_sender_recachea_tras_ttl():
    _reset_cache()
    import plugins._helpers as h
    # 1ª guarda con t=100; 2ª comprobación con t=500 (∆=400 > TTL=300) → re-consulta
    with _patch.object(h.api_users, "resolve_in_house", return_value="u1") as mock_api, \
         _patch.object(h.time, "monotonic", side_effect=[100.0, 500.0, 500.0]):
        h.resolve_sender("alice@x")
        h.resolve_sender("alice@x")
    assert mock_api.call_count == 2


# ── get_device / find_device_by_name ─────────────────────────────────────────

def test_get_device_filtra_por_id():
    devices = [{"id": "d1", "name": "Luz"}, {"id": "d2", "name": "TV"}]
    with _patch("plugins._helpers.api_devices.get_all", return_value=devices):
        from plugins._helpers import get_device
        assert get_device("d2") == {"id": "d2", "name": "TV"}


def test_get_device_devuelve_none_si_no_existe():
    with _patch("plugins._helpers.api_devices.get_all", return_value=[]):
        from plugins._helpers import get_device
        assert get_device("d2") is None


def test_find_device_por_substring_case_insensitive():
    devices = [{"id": "d1", "name": "Luz Salón"}, {"id": "d2", "name": "TV Dormitorio"}]
    with _patch("plugins._helpers.api_devices.get_all", return_value=devices):
        from plugins._helpers import find_device_by_name
        assert find_device_by_name("salón")["id"] == "d1"


def test_find_device_devuelve_none_si_no_matchea():
    with _patch("plugins._helpers.api_devices.get_all", return_value=[]):
        from plugins._helpers import find_device_by_name
        assert find_device_by_name("ghost") is None


# ── calculate_expected_state — acciones de volumen ───────────────────────────

def test_subir_volumen_incrementa_5():
    result = calculate_expected_state({"estado": {"volume": 40}}, "subir_volumen", {})
    assert result["volume"] == 45


def test_subir_volumen_clampa_a_100():
    result = calculate_expected_state({"estado": {"volume": 98}}, "subir_volumen", {})
    assert result["volume"] == 100


def test_bajar_volumen_decrementa_5():
    result = calculate_expected_state({"estado": {"volume": 50}}, "bajar_volumen", {})
    assert result["volume"] == 45


def test_bajar_volumen_clampa_a_0():
    result = calculate_expected_state({"estado": {"volume": 2}}, "bajar_volumen", {})
    assert result["volume"] == 0


# ── calculate_expected_state — color_rgb (ramas del color map) ───────────────

def test_color_rgb_nombre_conocido_asigna_hex():
    result = calculate_expected_state({}, "color_rgb", {"color": "azul"})
    assert result["color_hex"] == "#0000ff"
    assert result["work_mode"] == "colour"


def test_color_rgb_nombre_desconocido_no_asigna_hex():
    result = calculate_expected_state({}, "color_rgb", {"color": "salmon"})
    assert "color_hex" not in result
    assert result["work_mode"] == "colour"
