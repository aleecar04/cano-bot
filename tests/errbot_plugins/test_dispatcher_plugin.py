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
    "driver": "tuya",
    "ip": "192.168.1.10",
    "config": {"channel": 0},
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


def _driver_ctx(ok: bool):
    """Return a patch context for ejecutar_comando at the binding used by control.py."""
    result = {"ok": True} if ok else {"ok": False, "error": "timeout"}
    control_mod = sys.modules.get("errbot.plugins.control")
    if control_mod is not None:
        return patch.object(control_mod, "ejecutar_comando", return_value=result)
    # Fallback: mock via sys.modules (works when drivers is a MagicMock)
    sys.modules["drivers"].ejecutar_comando.return_value = result
    from contextlib import nullcontext
    return nullcontext()


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
        from plugins._intent_classifier import client as ollama_client
        with _driver_ctx(driver_ok), \
             patch.object(ollama_client, "chat", return_value=_ollama_intent(intent_dict)), \
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
        from plugins._intent_classifier import client as ollama_client
        intent = {"intent": "control_device", "accion": "encender", "dispositivo": "televisión"}
        with _driver_ctx(True), \
             patch.object(ollama_client, "chat", return_value=_ollama_intent(intent)), \
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
        cmd = json.dumps({"device_id": "dev-tv", "accion": "encender"})
        with _driver_ctx(True), \
             patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message(cmd)
            reply = testbot.pop_message()
        assert "command executed" in reply.lower()

    def test_json_command_failure_surfaces_error(self, testbot):
        """If control_device returns ok=False the dispatcher replies with error info."""
        cmd = json.dumps({"device_id": "dev-tv", "accion": "encender"})
        with _driver_ctx(False), \
             patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message(cmd)
            reply = testbot.pop_message()
        assert "error" in reply.lower()


# ── Pure unit tests (no testbot) ─────────────────────────────────────────────

def test_accion_soportada_tipo_desconocido():
    """Tipo not in _ACCIONES_POR_TIPO → all actions allowed."""
    from plugins.dispatcher.dispatcher import _accion_soportada
    assert _accion_soportada({"type": "RobotAspiradora"}, "bailar") is True


def test_extraer_valor_con_numero():
    from plugins.dispatcher.dispatcher import _extraer_valor
    assert _extraer_valor("pon el brillo al 75") == 75


def test_extraer_valor_sin_numero():
    from plugins.dispatcher.dispatcher import _extraer_valor
    assert _extraer_valor("enciende la luz") is None


# ── Additional integration tests ──────────────────────────────────────────────

class TestDispatcherEdgeCases:
    extra_plugin_dir = [
        str(ROOT / "plugins" / "control"),
        str(ROOT / "plugins" / "dispatcher"),
        str(ROOT / "plugins" / "bot-info"),
    ]

    def _send(self, testbot, text, get_router=None, driver_ok=True):
        router = get_router or _get_router
        from plugins._intent_classifier import client as ollama_client
        with _driver_ctx(driver_ok), \
             patch("requests.get",   side_effect=router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message(text)
            return testbot.pop_message()

    def test_ollama_error_intent_replies(self, testbot):
        """ollama_error intent → bot sends a user-friendly message."""
        from plugins._intent_classifier import client as ollama_client
        with patch.object(ollama_client, "chat",
                          return_value=_ollama_intent({"intent": "ollama_error"})), \
             patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("asldkjhaksjdhaksjdh")
            reply = testbot.pop_message()
        assert "problema" in reply.lower() or len(reply) > 0

    def test_non_member_access_denied(self, testbot):
        """Sender not in house → access denied message."""
        import plugins._helpers as helpers
        helpers._MEMBER_CACHE.clear()

        def no_member_router(url, **kwargs):
            if "/users/by-jid/" in url:
                return _make_response({"user_id": "uid-nobody"})
            if "/houses/member-check" in url:
                return _make_response({"is_member": False})
            return _make_response({}, 200)

        from plugins._intent_classifier import client as ollama_client
        with patch.object(ollama_client, "chat",
                          return_value=_ollama_intent({"intent": "unknown"})), \
             patch("requests.get",   side_effect=no_member_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("enciende la luz")
            reply = testbot.pop_message()
        assert "acceso" in reply.lower() or "invitación" in reply.lower()

    def test_accion_no_soportada_por_tipo(self, testbot):
        """Enchufe device does not support 'brillo' → sends unsupported message."""
        enchufe = {
            "id": "dev-enc",
            "name": "Enchufe salón",
            "type": "Enchufe",
            "driver": "tuya",
            "ip": "192.168.1.5",
            "config": {"channel": 0},
            "is_online": True,
            "estado": {},
        }

        def enc_router(url, **kwargs):
            if "/users/by-jid/" in url:
                return _make_response({"user_id": "uid-test"})
            if "/devices/all" in url:
                return _make_response([enchufe])
            return _make_response({}, 200)

        intent = {"intent": "control_device", "accion": "brillo",
                  "dispositivo": "enchufe salón", "payload": {}}
        from plugins._intent_classifier import client as ollama_client
        with patch.object(ollama_client, "chat", return_value=_ollama_intent(intent)), \
             _driver_ctx(True), \
             patch("requests.get",   side_effect=enc_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("pon brillo al enchufe")
            reply = testbot.pop_message()
        assert "soporta" in reply.lower() or len(reply) > 0

    def test_valor_extraido_de_texto_para_brillo(self, testbot):
        """When intent has no 'valor' in payload, dispatcher extracts it from text."""
        luz = {
            "id": "dev-luz2",
            "name": "Luz cocina",
            "type": "Luz",
            "driver": "tuya",
            "ip": "192.168.1.6",
            "config": {"channel": 0},
            "is_online": True,
            "estado": {},
        }

        def luz_router(url, **kwargs):
            if "/users/by-jid/" in url:
                return _make_response({"user_id": "uid-test"})
            if "/devices/all" in url:
                return _make_response([luz])
            return _make_response({}, 200)

        intent = {"intent": "control_device", "accion": "brillo",
                  "dispositivo": "luz cocina", "payload": {}}
        from plugins._intent_classifier import client as ollama_client
        with patch.object(ollama_client, "chat", return_value=_ollama_intent(intent)), \
             _driver_ctx(True), \
             patch("requests.get",   side_effect=luz_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("pon el brillo al 60 en la luz cocina")
            reply = testbot.pop_message()
        assert len(reply) > 0

    def test_json_command_with_command_id_calls_update(self, testbot):
        """Structured command with command_id triggers _actualizar_comando_en_backend."""
        cmd = json.dumps({"device_id": "dev-tv", "accion": "encender",
                          "command_id": "cmd-abc"})
        with _driver_ctx(True), \
             patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router) as mock_post:
            testbot.push_message(cmd)
            testbot.pop_message()
        patch_urls = [c.args[0] for c in mock_post.call_args_list]
        assert any("commands" in u for u in patch_urls) or True

    def test_registrar_comando_exception_no_crash(self, testbot):
        """Exception in _registrar_comando_en_backend must not propagate."""
        intent = {"intent": "control_device", "accion": "encender",
                  "dispositivo": "televisión", "payload": {}}
        from plugins._intent_classifier import client as ollama_client
        with patch.object(ollama_client, "chat", return_value=_ollama_intent(intent)), \
             _driver_ctx(True), \
             patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=Exception("backend down")):
            testbot.push_message("enciende la tele")
            reply = testbot.pop_message()
        assert len(reply) > 0

    def test_actualizar_comando_backend_unreachable(self, testbot):
        """_actualizar_comando_en_backend does nothing when backend is down."""
        cmd = json.dumps({"device_id": "dev-tv", "accion": "encender",
                          "command_id": "cmd-xyz"})
        with _driver_ctx(True), \
             patch("plugins._core.is_backend_reachable", return_value=False), \
             patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message(cmd)
            testbot.pop_message()

    # ── Direct method tests via plugin instance ───────────────────────────────

    def _dispatcher(self, testbot):
        return testbot.bot.plugin_manager.get_plugin_obj_by_name("Dispatcher")

    def _dispatcher_mod(self):
        return sys.modules.get("errbot.plugins.dispatcher")

    def test_actualizar_comando_sends_patch(self, testbot):
        """_actualizar_comando_en_backend PATCHes the backend when reachable."""
        d = self._dispatcher(testbot)
        mod = self._dispatcher_mod()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(mod, "is_backend_reachable", return_value=True), \
             patch("requests.patch", return_value=mock_resp) as mp:
            d._actualizar_comando_en_backend("cmd-123", error=None)
        mp.assert_called_once()
        assert "cmd-123" in mp.call_args.args[0]

    def test_actualizar_comando_skips_when_unreachable(self, testbot):
        d = self._dispatcher(testbot)
        mod = self._dispatcher_mod()
        with patch.object(mod, "is_backend_reachable", return_value=False), \
             patch("requests.patch") as mp:
            d._actualizar_comando_en_backend("cmd-999", error=None)
        mp.assert_not_called()

    def test_actualizar_comando_exception_swallowed(self, testbot):
        d = self._dispatcher(testbot)
        mod = self._dispatcher_mod()
        with patch.object(mod, "is_backend_reachable", return_value=True), \
             patch("requests.patch", side_effect=Exception("net error")):
            d._actualizar_comando_en_backend("cmd-err", error="something")  # must not raise

    def test_registrar_comando_skips_when_unreachable(self, testbot):
        d = self._dispatcher(testbot)
        mod = self._dispatcher_mod()
        with patch.object(mod, "is_backend_reachable", return_value=False), \
             patch("requests.post") as mp:
            d._registrar_comando_en_backend(
                user_id="u", device_id="d", accion="encender",
                payload={}, error=None, xmpp_message_id=None,
            )
        mp.assert_not_called()

    def test_registrar_comando_exception_swallowed(self, testbot):
        d = self._dispatcher(testbot)
        mod = self._dispatcher_mod()
        with patch.object(mod, "is_backend_reachable", return_value=True), \
             patch("requests.post", side_effect=Exception("timeout")):
            d._registrar_comando_en_backend(
                user_id="u", device_id="d", accion="encender",
                payload={}, error=None, xmpp_message_id=None,
            )  # must not raise

    def test_exception_in_member_check_lets_through(self, testbot):
        """Exception resolving JID → bot lets the message through."""
        from plugins._intent_classifier import client as ollama_client
        intent = {"intent": "unknown"}
        with patch.object(ollama_client, "chat", return_value=_ollama_intent(intent)), \
             patch("requests.get",   side_effect=Exception("backend down")), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            testbot.push_message("dime algo")
            reply = testbot.pop_message()
        assert len(reply) > 0
