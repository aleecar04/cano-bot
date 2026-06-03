import asyncio
import json
import uuid
from unittest.mock import MagicMock, patch


def _make_dispatcher():
    from plugins.dispatcher.dispatcher import Dispatcher
    d = Dispatcher.__new__(Dispatcher)
    d.log = MagicMock()
    d._bot = MagicMock()
    d.send = MagicMock()
    d.log_message = MagicMock()
    return d


def _msg(body="hola", frm="alice@x/res", correlation_id=None):
    m = MagicMock()
    m.body = body
    m.frm = frm
    m.extras = {"correlation_id": correlation_id} if correlation_id else {}
    return m


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if not asyncio.iscoroutine(coro) \
        else asyncio.run(coro)


# ── Standalone helpers ───────────────────────────────────────────────────────

class TestSplitCorrelation:

    def test_sin_pipe_devuelve_none_y_texto(self):
        from plugins.dispatcher.dispatcher import _split_correlation
        assert _split_correlation("hola mundo") == (None, "hola mundo")

    def test_con_uuid_valido_devuelve_uuid_y_texto(self):
        from plugins.dispatcher.dispatcher import _split_correlation
        cid = str(uuid.uuid4())
        cid_out, text = _split_correlation(f"{cid}|hola")
        assert cid_out == cid
        assert text == "hola"

    def test_con_pipe_pero_no_uuid_devuelve_none(self):
        from plugins.dispatcher.dispatcher import _split_correlation
        assert _split_correlation("no-uuid|hola") == (None, "no-uuid|hola")

    def test_strip_del_texto_tras_pipe(self):
        from plugins.dispatcher.dispatcher import _split_correlation
        cid = str(uuid.uuid4())
        _, text = _split_correlation(f"{cid}|  hola  ")
        assert text == "hola"


class TestNotUnderstand:

    def test_devuelve_uno_de_los_mensajes(self):
        from plugins.dispatcher.dispatcher import _not_understand, _NO_UNDERSTAND
        assert _not_understand() in _NO_UNDERSTAND


# ── _check_sender_access ─────────────────────────────────────────────────────

class TestCheckSenderAccess:

    def test_sender_resuelto_devuelve_id(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.resolve_sender", return_value="u1"):
            result = d._check_sender_access(_msg())
        assert result == "u1"

    def test_sin_sender_envia_mensaje_y_devuelve_none(self):
        d = _make_dispatcher()
        msg = _msg()
        with patch("plugins.dispatcher.dispatcher.resolve_sender", return_value=None):
            result = d._check_sender_access(msg)
        assert result is None
        d.send.assert_called_once()
        assert "acceso" in d.send.call_args[0][1].lower()

    def test_excepcion_devuelve_fail_open(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.resolve_sender", side_effect=RuntimeError("net")):
            result = d._check_sender_access(_msg())
        assert result == ""  # falsy distinto de None: sigue procesando


# ── _handle_structured_message ───────────────────────────────────────────────

class TestHandleStructuredMessage:

    def test_no_json_devuelve_false(self):
        d = _make_dispatcher()
        assert d._handle_structured_message("texto plano", _msg()) is False

    def test_poll_device_invoca_plugin(self):
        d = _make_dispatcher()
        method = MagicMock()
        d._bot.all_commands = {"poll_device": method}
        body = json.dumps({"type": "poll_device", "device_id": "d1"})
        assert d._handle_structured_message(body, _msg()) is True
        method.assert_called_once()

    def test_scan_llama_handle_scan(self):
        d = _make_dispatcher()
        d._handle_scan_command = MagicMock()
        body = json.dumps({"type": "scan", "command_id": "c1"})
        assert d._handle_structured_message(body, _msg()) is True
        d._handle_scan_command.assert_called_once()

    def test_relay_invoca_reply(self):
        d = _make_dispatcher()
        body = json.dumps({"type": "relay", "text": "hola"})
        msg = _msg()
        assert d._handle_structured_message(body, msg) is True
        d.send.assert_called_once_with(msg.frm, "hola")

    def test_device_id_y_action_invoca_handle_device(self):
        d = _make_dispatcher()
        body = json.dumps({"device_id": "d1", "action": "encender", "payload": {}})
        with patch("plugins.dispatcher.dispatcher.handle_device_command") as mock_h:
            assert d._handle_structured_message(body, _msg()) is True
        mock_h.assert_called_once()

    def test_natural_classified_devuelve_false(self):
        """natural_classified no se considera 'handled' aquí; lo procesa _extract más adelante."""
        d = _make_dispatcher()
        body = json.dumps({"type": "natural_classified", "intent_data": {"intent": "ayuda"}})
        assert d._handle_structured_message(body, _msg()) is False


# ── _extract_natural_classified ──────────────────────────────────────────────

class TestExtractNaturalClassified:

    def test_no_json_devuelve_none(self):
        d = _make_dispatcher()
        intent, text = d._extract_natural_classified("texto plano")
        assert intent is None
        assert text == "texto plano"

    def test_json_pero_no_natural_classified(self):
        d = _make_dispatcher()
        body = json.dumps({"type": "scan"})
        intent, text = d._extract_natural_classified(body)
        assert intent is None
        assert text == body

    def test_natural_classified_devuelve_intent_y_original(self):
        d = _make_dispatcher()
        body = json.dumps({
            "type": "natural_classified",
            "intent_data": {"intent": "ayuda"},
            "original_body": "ayudame",
        })
        intent, text = d._extract_natural_classified(body)
        assert intent == {"intent": "ayuda"}
        assert text == "ayudame"

    def test_natural_classified_sin_intent_data(self):
        d = _make_dispatcher()
        body = json.dumps({"type": "natural_classified"})
        intent, text = d._extract_natural_classified(body)
        assert intent == {}
        assert text == ""


# ── _forward_natural_to_backend ──────────────────────────────────────────────

class TestForwardNaturalToBackend:

    def test_backend_unreachable_envia_mensaje(self):
        d = _make_dispatcher()
        msg = _msg()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=False):
            d._forward_natural_to_backend(msg, "hola")
        d.send.assert_called_once()
        assert "disponible" in d.send.call_args[0][1]

    def test_backend_ok_llama_forward(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_messages.forward_from_gajim") as mock_f:
            d._forward_natural_to_backend(_msg(), "hola")
        mock_f.assert_called_once()

    def test_forward_excepcion_envia_error(self):
        d = _make_dispatcher()
        msg = _msg()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_messages.forward_from_gajim",
                   side_effect=RuntimeError("net")):
            d._forward_natural_to_backend(msg, "hola")
        d.send.assert_called_once()
        assert "procesar" in d.send.call_args[0][1].lower()


# ── _dispatch_intent ─────────────────────────────────────────────────────────

class TestDispatchIntent:

    def test_scan_devices_llama_chat_query(self):
        d = _make_dispatcher()
        d._handle_chat_query = MagicMock()
        d._dispatch_intent({"intent": "scan_devices"}, _msg(), "scan", "u1")
        d._handle_chat_query.assert_called_once()
        assert d._handle_chat_query.call_args.kwargs["action"] == "scan_devices"

    def test_list_devices_llama_chat_query(self):
        d = _make_dispatcher()
        d._handle_chat_query = MagicMock()
        d._dispatch_intent({"intent": "list_devices"}, _msg(), "lista", "u1")
        d._handle_chat_query.assert_called_once()
        assert d._handle_chat_query.call_args.kwargs["action"] == "list_devices"

    def test_info_intent_invoca_plugin(self):
        d = _make_dispatcher()
        d._invoke_info_plugin = MagicMock(return_value=True)
        d._dispatch_intent({"intent": "ayuda"}, _msg(), "hola", "u1")
        d._invoke_info_plugin.assert_called_once()
        args = d._invoke_info_plugin.call_args[0]
        assert args[0] == "ayuda"  # cmd_name del intent_map

    def test_intent_desconocido_cae_a_not_understand(self):
        d = _make_dispatcher()
        d._reply = MagicMock()
        d._dispatch_intent({"intent": "inventado"}, _msg(), "x", "u1")
        d._reply.assert_called_once()

    def test_invoke_devuelve_false_cae_a_not_understand(self):
        d = _make_dispatcher()
        d._invoke_info_plugin = MagicMock(return_value=False)
        d._reply = MagicMock()
        d._dispatch_intent({"intent": "ayuda"}, _msg(), "x", "u1")
        d._reply.assert_called_once()


# ── _invoke_info_plugin ──────────────────────────────────────────────────────

class TestInvokeInfoPlugin:

    def test_plugin_no_existe_devuelve_false(self):
        d = _make_dispatcher()
        d._bot.all_commands = {}
        result = d._invoke_info_plugin("ayuda", "ayuda", {}, _msg(), "x", "u1")
        assert result is False

    def test_plugin_ejecuta_y_registra(self):
        d = _make_dispatcher()
        plugin = MagicMock(return_value="HELP TEXT")
        d._bot.all_commands = {"ayuda": plugin}
        d._reply = MagicMock()
        d._register_command_in_backend = MagicMock()
        result = d._invoke_info_plugin("ayuda", "ayuda", {}, _msg(), "x", "u1")
        assert result is True
        plugin.assert_called_once()
        d._reply.assert_called_once()
        d._register_command_in_backend.assert_called_once()

    def test_acciones_pasa_dispositivo_como_args(self):
        d = _make_dispatcher()
        plugin = MagicMock(return_value="info")
        d._bot.all_commands = {"acciones": plugin}
        d._reply = MagicMock()
        d._register_command_in_backend = MagicMock()
        d._invoke_info_plugin("acciones", "acciones", {"dispositivo": "luz"}, _msg(), "x", "u1")
        plugin.assert_called_once()
        assert plugin.call_args[0][1] == "luz"

    def test_otras_acciones_pasan_args_vacios(self):
        d = _make_dispatcher()
        plugin = MagicMock(return_value="info")
        d._bot.all_commands = {"ayuda": plugin}
        d._reply = MagicMock()
        d._register_command_in_backend = MagicMock()
        d._invoke_info_plugin("ayuda", "ayuda", {"dispositivo": "luz"}, _msg(), "x", "u1")
        assert plugin.call_args[0][1] == ""


# ── _run_plugin ──────────────────────────────────────────────────────────────

class TestRunPlugin:

    def test_plugin_no_existe_devuelve_error(self):
        d = _make_dispatcher()
        d._bot.all_commands = {}
        result = d._run_plugin(_msg(), "no_existe")
        assert result["tipo"] == "error"

    def test_plugin_existe_devuelve_resultado(self):
        d = _make_dispatcher()
        plugin = MagicMock(return_value={"tipo": "ok", "data": 1})
        d._bot.all_commands = {"x": plugin}
        result = d._run_plugin(_msg(), "x")
        assert result == {"tipo": "ok", "data": 1}


# ── _handle_scan_command ─────────────────────────────────────────────────────

class TestHandleScanCommand:

    def test_scan_ok_actualiza_con_result_data(self):
        d = _make_dispatcher()
        plugin = MagicMock(return_value={"tipo": "scan_response", "dispositivos": []})
        d._bot.all_commands = {"scan_devices": plugin}
        d._update_command_in_backend = MagicMock()
        d._handle_scan_command(_msg(), "c1")
        d._update_command_in_backend.assert_called_once()
        assert d._update_command_in_backend.call_args.kwargs["error"] is None

    def test_scan_error_actualiza_con_error(self):
        d = _make_dispatcher()
        plugin = MagicMock(return_value={"tipo": "error", "mensaje": "falló"})
        d._bot.all_commands = {"scan_devices": plugin}
        d._update_command_in_backend = MagicMock()
        d._handle_scan_command(_msg(), "c1")
        d._update_command_in_backend.assert_called_once()
        assert d._update_command_in_backend.call_args.kwargs["error"] == "falló"


# ── _handle_chat_query ───────────────────────────────────────────────────────

class TestHandleChatQuery:

    def test_sin_sender_no_hace_nada(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.resolve_sender", return_value=None):
            d._handle_chat_query(_msg(), "x", action="scan_devices", command_name="scan_devices")

    def test_backend_off_ejecuta_y_responde_sin_registrar(self):
        d = _make_dispatcher()
        d._reply = MagicMock()
        plugin = MagicMock(return_value={"tipo": "ok"})
        d._bot.all_commands = {"scan_devices": plugin}
        with patch("plugins.dispatcher.dispatcher.resolve_sender", return_value="u1"), \
             patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=False):
            d._handle_chat_query(_msg(), "x", action="scan_devices", command_name="scan_devices")
        plugin.assert_called_once()
        d._reply.assert_called_once()

    def test_camino_feliz_registra_pending_y_actualiza(self):
        d = _make_dispatcher()
        d._reply = MagicMock()
        d._update_command_in_backend = MagicMock()
        plugin = MagicMock(return_value={"tipo": "ok"})
        d._bot.all_commands = {"scan_devices": plugin}
        with patch("plugins.dispatcher.dispatcher.resolve_sender", return_value="u1"), \
             patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_commands.register_pending_from_bot",
                   return_value={"command_id": "c1"}) as mock_reg:
            d._handle_chat_query(_msg(), "x", action="scan_devices", command_name="scan_devices")
        mock_reg.assert_called_once()
        d._update_command_in_backend.assert_called_once_with(
            "c1", error=None, result_data={"tipo": "ok"}
        )

    def test_register_pending_falla_pero_ejecuta_igual(self):
        d = _make_dispatcher()
        d._reply = MagicMock()
        plugin = MagicMock(return_value={"tipo": "ok"})
        d._bot.all_commands = {"scan_devices": plugin}
        with patch("plugins.dispatcher.dispatcher.resolve_sender", return_value="u1"), \
             patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_commands.register_pending_from_bot",
                   side_effect=RuntimeError("net")):
            d._handle_chat_query(_msg(), "x", action="scan_devices", command_name="scan_devices")
        plugin.assert_called_once()  # se ejecuta aunque el register falle


# ── _update_command_in_backend / _register_command_in_backend ────────────────

class TestUpdateAndRegisterBackend:

    def test_update_skip_si_backend_off(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=False), \
             patch("plugins.dispatcher.dispatcher.api_commands.patch_result") as mock_p:
            d._update_command_in_backend("c1", error=None)
        mock_p.assert_not_called()

    def test_update_llama_patch_result(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_commands.patch_result") as mock_p:
            d._update_command_in_backend("c1", error="boom", result_data={"x": 1})
        mock_p.assert_called_once_with("c1", "boom", {"x": 1})

    def test_update_silencia_excepcion(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_commands.patch_result",
                   side_effect=RuntimeError("boom")):
            d._update_command_in_backend("c1", error=None)  # no lanza

    def test_register_skip_si_backend_off(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=False), \
             patch("plugins.dispatcher.dispatcher.api_commands.register_from_bot") as mock_r:
            d._register_command_in_backend(
                user_id="u1", device_id=None, action="ayuda", payload={},
                error=None, message_id=None,
            )
        mock_r.assert_not_called()

    def test_register_llama_api(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_commands.register_from_bot") as mock_r:
            d._register_command_in_backend(
                user_id="u1", device_id=None, action="ayuda", payload={},
                error=None, message_id=None,
            )
        mock_r.assert_called_once()

    def test_register_silencia_excepcion(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_commands.register_from_bot",
                   side_effect=RuntimeError("boom")):
            d._register_command_in_backend(
                user_id="u1", device_id=None, action="ayuda", payload={},
                error=None, message_id=None,
            )


# ── _get_command_from_plugins / _reply ───────────────────────────────────────

class TestSmallHelpers:

    def test_get_command_devuelve_del_bot(self):
        d = _make_dispatcher()
        plugin = MagicMock()
        d._bot.all_commands = {"foo": plugin}
        assert d._get_command_from_plugins("foo") is plugin

    def test_get_command_devuelve_none_si_no_existe(self):
        d = _make_dispatcher()
        d._bot.all_commands = {}
        assert d._get_command_from_plugins("foo") is None

    def test_reply_loguea_y_envia(self):
        d = _make_dispatcher()
        msg = _msg()
        d._reply(msg, "tx", "respuesta")
        d.log_message.assert_called_once()
        d.send.assert_called_once_with(msg.frm, "respuesta")


# ── callback_message (orquestador) ───────────────────────────────────────────

class TestCallbackMessage:

    def test_body_vacio_no_hace_nada(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock()
        msg = _msg(body="   ")
        _run(d.callback_message(msg))
        d._check_sender_access.assert_not_called()

    def test_sin_sender_corta_flujo(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value=None)
        d._handle_structured_message = MagicMock()
        _run(d.callback_message(_msg(body="hola")))
        d._handle_structured_message.assert_not_called()

    def test_structured_consumido_corta(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value="u1")
        d._handle_structured_message = MagicMock(return_value=True)
        d._extract_natural_classified = MagicMock()
        _run(d.callback_message(_msg(body="hola")))
        d._extract_natural_classified.assert_not_called()

    def test_sin_intent_reenvia_al_backend(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value="u1")
        d._handle_structured_message = MagicMock(return_value=False)
        d._extract_natural_classified = MagicMock(return_value=(None, "hola"))
        d._forward_natural_to_backend = MagicMock()
        d._dispatch_intent = MagicMock()
        _run(d.callback_message(_msg(body="hola")))
        d._forward_natural_to_backend.assert_called_once()
        d._dispatch_intent.assert_not_called()

    def test_con_intent_dispatcha(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value="u1")
        d._handle_structured_message = MagicMock(return_value=False)
        d._extract_natural_classified = MagicMock(return_value=({"intent": "ayuda"}, "hola"))
        d._dispatch_intent = MagicMock()
        _run(d.callback_message(_msg(body="hola")))
        d._dispatch_intent.assert_called_once()

    def test_setea_correlation_id_en_extras(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value="u1")
        d._handle_structured_message = MagicMock(return_value=True)
        cid = str(uuid.uuid4())
        msg = _msg(body=f"{cid}|hola")
        _run(d.callback_message(msg))
        assert msg.extras["correlation_id"] == cid
