"""
Integration tests for the Dispatcher errbot plugin.

Both 'control' and 'dispatcher' plugins are loaded so that
Dispatcher._get_command_from_plugins("control_device") can find the real command.

Natural-language flow: push_message(text without !) → Dispatcher.callback_message
  → classify_intent (mocked Ollama) → route to control_device or other command.

NOTE on driver mocking: same as test_control_plugin — configure return_value on
  the existing MagicMock child; do NOT replace the attribute.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).parent.parent.parent

# Load both plugins so dispatcher can delegate to control_device
extra_plugin_dir = [
    str(ROOT / "plugins" / "control"),
    str(ROOT / "plugins" / "dispatcher"),
]

# ── Fake data ─────────────────────────────────────────────────────────────────

DEVICE_TV = {
    "id": "dev-tv",
    "name": "Televisión",
    "type": "SmartTV",
    "driver": "lgtv",
    "is_online": True,
    "estado": {"power": "off"},
}


# ── HTTP stubs ────────────────────────────────────────────────────────────────

def _make_response(data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


def _get_router(url, **kwargs):
    if "/users/by-jid/" in url:
        return _make_response({"user_id": "uid-test"})
    if "/devices/all" in url:
        return _make_response([DEVICE_TV])
    return _make_response({}, 200)  # /health etc.


def _patch_router(url, **kwargs):
    return _make_response({}, 200)


def _post_router(url, **kwargs):
    return _make_response({}, 200)


def _set_driver(ok: bool):
    """Configure the already-imported ejecutar_comando mock (not replace it)."""
    drivers = sys.modules["drivers"]
    if ok:
        drivers.ejecutar_comando.return_value = {"ok": True}
    else:
        drivers.ejecutar_comando.return_value = {"ok": False, "error": "timeout"}


def _ollama_intent(intent_dict: dict):
    """Build the ollama client.chat() return value for a given intent dict."""
    return {"message": {"content": json.dumps(intent_dict)}}


# ── Natural language routing ──────────────────────────────────────────────────

class TestNaturalLanguageDispatch:
    extra_plugin_dir = [
        str(ROOT / "plugins" / "control"),
        str(ROOT / "plugins" / "dispatcher"),
    ]

    def _push_natural(self, testbot, text, intent_dict, driver_ok=True):
        """Send a natural-language message and return the bot reply."""
        _set_driver(driver_ok)
        from plugins._intent_classifier import client as ollama_client
        with patch.object(ollama_client, "chat", return_value=_ollama_intent(intent_dict)), \
             patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message(text)
            return testbot.pop_message()

    def test_encender_device_ok(self, testbot):
        intent = {"intent": "control_device", "accion": "encender", "dispositivo": "televisión"}
        reply = self._push_natural(testbot, "enciende la tele", intent)
        assert any(w in reply.lower() for w in ("televisión", "encender", "ejecutado"))

    def test_apagar_device_ok(self, testbot):
        intent = {"intent": "control_device", "accion": "apagar", "dispositivo": "televisión"}
        reply = self._push_natural(testbot, "apaga la tele", intent)
        assert any(w in reply.lower() for w in ("televisión", "apagar", "ejecutado"))

    def test_device_not_found_friendly_message(self, testbot):
        intent = {"intent": "control_device", "accion": "encender", "dispositivo": "nevera"}
        reply = self._push_natural(testbot, "enciende la nevera", intent)
        assert "no he encontrado" in reply.lower() or "dispositivo" in reply.lower()

    def test_missing_dispositivo_field_returns_error(self, testbot):
        intent = {"intent": "control_device", "accion": "encender", "dispositivo": ""}
        reply = self._push_natural(testbot, "enciende", intent)
        assert len(reply) > 0
        assert "no he entendido" in reply.lower() or "dispositivo" in reply.lower()

    def test_missing_accion_field_returns_error(self, testbot):
        intent = {"intent": "control_device", "accion": "", "dispositivo": "televisión"}
        reply = self._push_natural(testbot, "haz algo con la tele", intent)
        assert len(reply) > 0

    def test_driver_failure_surfaces_error(self, testbot):
        intent = {"intent": "control_device", "accion": "encender", "dispositivo": "televisión"}
        reply = self._push_natural(testbot, "enciende la tele", intent, driver_ok=False)
        assert len(reply) > 0

    def test_unknown_intent_returns_not_understand(self, testbot):
        intent = {"intent": "unknown"}
        reply = self._push_natural(testbot, "¿cuál es tu serie favorita?", intent)
        assert len(reply) > 0
        from plugins.dispatcher.dispatcher import _NO_UNDERSTAND
        assert reply in _NO_UNDERSTAND

    def test_not_understand_rotates_through_messages(self, testbot):
        """Three consecutive unknowns should cycle through _NO_UNDERSTAND list."""
        from plugins.dispatcher.dispatcher import _NO_UNDERSTAND
        intent = {"intent": "unknown"}
        replies = []
        for _ in range(len(_NO_UNDERSTAND)):
            reply = self._push_natural(testbot, "bla bla", intent)
            replies.append(reply)
        # All replies must come from the known list
        assert all(r in _NO_UNDERSTAND for r in replies)
        # Rotation means not all are the same after a full cycle
        assert len(set(replies)) > 1



# ── Intent map routing (saludo, list_devices, mi_ip) ─────────────────────────

class TestIntentMapRouting:
    extra_plugin_dir = [
        str(ROOT / "plugins" / "control"),
        str(ROOT / "plugins" / "dispatcher"),
        str(ROOT / "plugins" / "bot-info"),
    ]

    def _push_intent(self, testbot, text, intent_dict):
        from plugins._intent_classifier import client as ollama_client
        with patch.object(ollama_client, "chat", return_value=_ollama_intent(intent_dict)), \
             patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message(text)
            return testbot.pop_message()

    def test_list_devices_intent_routes_to_control(self, testbot):
        reply = self._push_intent(testbot, "qué dispositivos tengo", {"intent": "list_devices"})
        data = json.loads(reply)
        assert data["tipo"] == "device_list"

    def test_saludo_intent_routes_to_who_are_you(self, testbot):
        reply = self._push_intent(testbot, "hola bot", {"intent": "saludo"})
        assert "cano-bot" in reply.lower() or "asistente" in reply.lower()

    def test_registrar_comando_skips_when_backend_unreachable(self, testbot):
        """_registrar_comando_en_backend must not crash when backend is down."""
        _set_driver(True)
        from plugins._intent_classifier import client as ollama_client
        intent = {"intent": "control_device", "accion": "encender", "dispositivo": "televisión"}
        with patch.object(ollama_client, "chat", return_value=_ollama_intent(intent)), \
             patch("plugins._core.is_backend_reachable", return_value=False), \
             patch("requests.get",   side_effect=_get_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("enciende la tele")
            reply = testbot.pop_message()
        assert len(reply) > 0


# ── Exclamation-mark commands bypass callback_message ────────────────────────

class TestBotcmdPassthrough:
    extra_plugin_dir = [
        str(ROOT / "plugins" / "control"),
        str(ROOT / "plugins" / "dispatcher"),
    ]

    def test_exclamation_list_devices_handled_by_control(self, testbot):
        """!-prefixed messages go to the errbot command router, not callback_message."""
        with patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("!list_devices")
            msg = testbot.pop_message()
        data = json.loads(msg)
        assert "tipo" in data


# ── Structured JSON command (from backend via XMPP) ──────────────────────────

class TestStructuredDeviceCommand:
    extra_plugin_dir = [
        str(ROOT / "plugins" / "control"),
        str(ROOT / "plugins" / "dispatcher"),
    ]

    def test_json_device_command_ok(self, testbot):
        """A plain JSON message with device_id+accion is routed via _handle_device_command."""
        _set_driver(True)
        cmd = json.dumps({"device_id": "dev-tv", "accion": "encender"})
        with patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message(cmd)
            reply = testbot.pop_message()
        assert "command executed" in reply.lower()

    def test_json_command_failure_surfaces_error(self, testbot):
        """If control_device returns ok=False the dispatcher replies with error info."""
        _set_driver(False)
        cmd = json.dumps({"device_id": "dev-tv", "accion": "encender"})
        with patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message(cmd)
            reply = testbot.pop_message()
        assert "error" in reply.lower()
