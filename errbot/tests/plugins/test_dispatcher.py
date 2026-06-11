import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from plugins.dispatcher.dispatcher import Dispatcher, _split_correlation


def _make_dispatcher():
    d = Dispatcher.__new__(Dispatcher)
    d.log = MagicMock()
    d._bot = MagicMock()
    d.send = MagicMock()
    d.log_message = MagicMock()
    return d


def _msg(body="hola", frm="anabel@xmpp.cano-app.com", correlation_id=None):
    m = MagicMock()
    m.body = body
    m.frm = frm
    m.extras = {"correlation_id": correlation_id} if correlation_id else {}
    return m


_VALID_UUID = str(uuid.uuid4())


class TestDispatcherPlugin:

    @pytest.mark.parametrize("text, expected", [
        ("no-uuid|hola", (None, "no-uuid|hola")),
        (f"{_VALID_UUID}|  hola  ", (_VALID_UUID, "hola")),
    ])
    def test_split_correlation(self, text, expected):
        assert _split_correlation(text) == expected

    def test_blocks_unknown_sender_and_warns(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.resolve_sender", return_value=None):
            assert d._check_sender_access(_msg()) is None
        d.send.assert_called_once()

    def test_poll_device_invokes_plugin(self):
        d = _make_dispatcher()
        poll = MagicMock()
        d._bot.all_commands = {"poll_device": poll}
        assert d._handle_structured_message(
            json.dumps({"type": "poll_device", "device_id": "device_lampara"}), _msg()) is True
        poll.assert_called_once()

    def test_scan_invokes_scan_handler(self):
        d = _make_dispatcher()
        d._handle_scan_command = MagicMock()
        assert d._handle_structured_message(
            json.dumps({"type": "scan", "command_id": "cmd_encender"}), _msg()) is True
        d._handle_scan_command.assert_called_once()

    def test_device_command_dispatches_to_handler(self):
        d = _make_dispatcher()
        body = json.dumps({"device_id": "device_lampara", "action": "encender", "payload": {}})
        with patch("plugins.dispatcher.dispatcher.handle_device_command") as mock_dev:
            assert d._handle_structured_message(body, _msg()) is True
        mock_dev.assert_called_once()

    @pytest.mark.parametrize("body, expected_intent, expected_text", [
        ("texto ejemplo", None, "texto ejemplo"),
        (
            json.dumps({"type": "natural_classified", "intent_data": {"intent": "ayuda"}, "original_body": "ayudame"}),
            {"intent": "ayuda"},
            "ayudame",
        ),
    ])
    def test_extract_natural_classified(self, body, expected_intent, expected_text):
        intent, text = _make_dispatcher()._extract_natural_classified(body)
        assert intent == expected_intent
        assert text == expected_text

    def test_forward_natural_warns_user_when_backend_unreachable(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=False):
            d._forward_natural_to_backend(_msg(), "hola")
        d.send.assert_called_once()

    def test_forward_natural_replies_error_when_api_fails(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_messages.forward_from_gajim",
                   side_effect=RuntimeError("net")):
            d._forward_natural_to_backend(_msg(), "hola")
        d.send.assert_called_once()

    def test_query_intents_route_to_chat_query(self):
        d = _make_dispatcher()
        d._handle_chat_query = MagicMock()
        d._dispatch_intent({"intent": "scan_devices"}, _msg(), "x", "user_anabel")
        assert d._handle_chat_query.call_args.kwargs["action"] == "scan_devices"

    def test_unknown_plugin_falls_back_to_not_understand(self):
        d = _make_dispatcher()
        d._reply = MagicMock()
        d._dispatch_intent({"intent": "inventado"}, _msg(), "x", "user_anabel")
        d._reply.assert_called_once()

    def test_only_acciones_command_receives_device_arg(self):
        d = _make_dispatcher()
        d._reply = MagicMock()
        d._register_command_in_backend = MagicMock()
        plugin = MagicMock(return_value="info")
        d._bot.all_commands = {"acciones": plugin}
        d._invoke_info_plugin("acciones", "acciones", {"device": "luz"}, _msg(), "x", "user_anabel")
        assert plugin.call_args[0][1] == "luz"

    @pytest.mark.parametrize("plugin_result, expected_error", [
        ({"tipo": "ok"}, None),
        ({"tipo": "error", "mensaje": "boom"}, "boom"),
    ])
    def test_handle_scan_updates_backend(self, plugin_result, expected_error):
        d = _make_dispatcher()
        d._update_command_in_backend = MagicMock()
        d._bot.all_commands = {"scan_devices": MagicMock(return_value=plugin_result)}
        d._handle_scan_command(_msg(), "cmd_encender")
        assert d._update_command_in_backend.call_args.kwargs["error"] == expected_error

    def test_handle_chat_query_registers_and_updates(self):
        d = _make_dispatcher()
        d._reply = MagicMock()
        d._update_command_in_backend = MagicMock()
        d._bot.all_commands = {"scan_devices": MagicMock(return_value={"tipo": "ok"})}
        with patch("plugins.dispatcher.dispatcher.resolve_sender", return_value="user_anabel"), \
             patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_commands.register_pending_from_bot",
                   return_value={"command_id": "cmd_encender"}):
            d._handle_chat_query(_msg(), "x", action="scan_devices", command_name="scan_devices")
        d._update_command_in_backend.assert_called_once_with("cmd_encender", error=None, result_data={"tipo": "ok"})

    def test_update_command_skips_api_when_offline(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=False), \
             patch("plugins.dispatcher.dispatcher.api_commands.patch_result") as mock_fn:
            d._update_command_in_backend("cmd_encender", error="boom")
        mock_fn.assert_not_called()

    def test_register_command_silences_api_exception(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_commands.register_from_bot",
                   side_effect=RuntimeError("boom")):
            d._register_command_in_backend(
                user_id="user_anabel", device_id=None, action="ayuda",
                payload={}, error=None, message_id=None,
            )

    def test_callback_aborts_when_unauthorized_or_empty(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value=None)
        d._handle_structured_message = MagicMock()
        d.callback_message(_msg(body="hola"))
        d._handle_structured_message.assert_not_called()

        d._check_sender_access.reset_mock()
        d.callback_message(_msg(body="   "))
        d._check_sender_access.assert_not_called()

    def test_callback_message_no_intent_forwards_to_backend(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value="user_anabel")
        d._handle_structured_message = MagicMock(return_value=False)
        d._extract_natural_classified = MagicMock(return_value=(None, "hola"))
        d._forward_natural_to_backend = MagicMock()
        d._dispatch_intent = MagicMock()
        d.callback_message(_msg(body="hola"))
        d._forward_natural_to_backend.assert_called_once()
        d._dispatch_intent.assert_not_called()

    def test_callback_message_intent_present_dispatches(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value="user_anabel")
        d._handle_structured_message = MagicMock(return_value=False)
        d._extract_natural_classified = MagicMock(return_value=({"intent": "ayuda"}, "hola"))
        d._dispatch_intent = MagicMock()
        d.callback_message(_msg(body="hola"))
        d._dispatch_intent.assert_called_once()

    def test_callback_stores_correlation_id_in_extras(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value="user_anabel")
        d._handle_structured_message = MagicMock(return_value=True)
        cid = str(uuid.uuid4())
        msg = _msg(body=f"{cid}|hola")
        d.callback_message(msg)
        assert msg.extras["correlation_id"] == cid
