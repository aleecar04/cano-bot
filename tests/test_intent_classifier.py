"""
Tests for plugins/_intent_classifier.py — classify_intent.

Ollama is mocked at sys.modules level (see conftest.py), so the module-level
  client = ollama.Client(host=OLLAMA_HOST)
creates a MagicMock. Each test then patches client.chat to control the response.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


def _ollama_response(content: str) -> dict:
    """Build a fake ollama chat() return value."""
    return {"message": {"content": content}}


def _classify(content: str) -> dict:
    """Call classify_intent with ollama returning the given raw content string."""
    from plugins._intent_classifier import classify_intent, client
    with patch.object(client, "chat", return_value=_ollama_response(content)):
        return classify_intent("texto de prueba")


# ── Happy path ────────────────────────────────────────────────────────────────

def test_control_device_intent_parsed():
    payload = {"intent": "control_device", "accion": "encender", "dispositivo": "luz salon"}
    result = _classify(json.dumps(payload))
    assert result["intent"] == "control_device"
    assert result["accion"] == "encender"
    assert result["dispositivo"] == "luz salon"


def test_list_devices_intent():
    result = _classify(json.dumps({"intent": "list_devices"}))
    assert result["intent"] == "list_devices"


def test_scan_devices_intent():
    result = _classify(json.dumps({"intent": "scan_devices"}))
    assert result["intent"] == "scan_devices"


def test_saludo_intent():
    result = _classify(json.dumps({"intent": "saludo"}))
    assert result["intent"] == "saludo"


def test_mi_ip_intent():
    result = _classify(json.dumps({"intent": "mi_ip"}))
    assert result["intent"] == "mi_ip"


def test_unknown_intent_passthrough():
    result = _classify(json.dumps({"intent": "unknown"}))
    assert result["intent"] == "unknown"


def test_extra_whitespace_stripped():
    """LLMs often add trailing newlines; strip() must handle it."""
    payload = "  " + json.dumps({"intent": "mi_ip"}) + "\n\n"
    result = _classify(payload)
    assert result["intent"] == "mi_ip"


def test_control_device_with_payload():
    payload = {
        "intent": "control_device",
        "accion": "brillo",
        "dispositivo": "lampara",
        "payload": {"valor": 80},
    }
    result = _classify(json.dumps(payload))
    assert result["accion"] == "brillo"
    assert result.get("payload", {}).get("valor") == 80


# ── Error handling ────────────────────────────────────────────────────────────

def test_invalid_json_returns_unknown():
    result = _classify("esto no es JSON {{{")
    assert result == {"intent": "unknown"}


def test_partial_json_returns_unknown():
    result = _classify('{"intent": "control_device"')  # unclosed brace
    assert result == {"intent": "unknown"}


def test_plain_text_returns_unknown():
    result = _classify("Enciende la luz del salón.")
    assert result == {"intent": "unknown"}


def test_exception_from_ollama_returns_unknown():
    from plugins._intent_classifier import classify_intent, client
    with patch.object(client, "chat", side_effect=ConnectionError("ollama offline")):
        result = classify_intent("enciende la luz")
    assert result == {"intent": "unknown"}


def test_generic_exception_returns_unknown():
    from plugins._intent_classifier import classify_intent, client
    with patch.object(client, "chat", side_effect=RuntimeError("unexpected")):
        result = classify_intent("test")
    assert result == {"intent": "unknown"}


def test_empty_response_content_returns_unknown():
    result = _classify("")
    assert result == {"intent": "unknown"}
