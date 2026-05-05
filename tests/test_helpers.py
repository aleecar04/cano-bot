"""Tests for plugins/_helpers.py — calculate_expected_state (pure function)."""
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
