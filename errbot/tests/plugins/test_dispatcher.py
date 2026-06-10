import json
import uuid
from unittest.mock import MagicMock, patch

import pytest


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


_VALID_UUID = str(uuid.uuid4())


@pytest.mark.parametrize("text, expected", [
    ("no-uuid|hola", (None, "no-uuid|hola")),
    (f"{_VALID_UUID}|  hola  ", (_VALID_UUID, "hola")),
])
def test_split_correlation(text, expected):
    from plugins.dispatcher.dispatcher import _split_correlation
    assert _split_correlation(text) == expected


class TestCheckSenderAccess:

    def test_blocks_unknown_sender_and_warns(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.resolve_sender", return_value=None):
            assert d._check_sender_access(_msg()) is None
        d.send.assert_called_once()

class TestHandleStructuredMessage:

    def test_poll_device_invokes_plugin(self):
        d = _make_dispatcher()
        poll = MagicMock()
        d._bot.all_commands = {"poll_device": poll}
        assert d._handle_structured_message(
            json.dumps({"type": "poll_device", "device_id": "d1"}), _msg()) is True
        poll.assert_called_once()

    def test_scan_invokes_scan_handler(self):
        d = _make_dispatcher()
        d._handle_scan_command = MagicMock()
        assert d._handle_structured_message(
            json.dumps({"type": "scan", "command_id": "c1"}), _msg()) is True
        d._handle_scan_command.assert_called_once()

    def test_device_command_dispatches_to_handler(self):
        d = _make_dispatcher()
        body = json.dumps({"device_id": "d1", "action": "encender", "payload": {}})
        with patch("plugins.dispatcher.dispatcher.handle_device_command") as mock_dev:
            assert d._handle_structured_message(body, _msg()) is True
        mock_dev.assert_called_once()


@pytest.mark.parametrize("body, expected_intent, expected_text", [
    ("texto plano", None, "texto plano"),
    (
        json.dumps({"type": "natural_classified", "intent_data": {"intent": "ayuda"}, "original_body": "ayudame"}),
        {"intent": "ayuda"},
        "ayudame",
    ),
])
def test_extract_natural_classified(body, expected_intent, expected_text):
    intent, text = _make_dispatcher()._extract_natural_classified(body)
    assert intent == expected_intent
    assert text == expected_text


class TestForwardNaturalToBackend:

    def test_warns_user_when_backend_unreachable(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=False):
            d._forward_natural_to_backend(_msg(), "hola")
        d.send.assert_called_once()

    def test_forwards_to_api_when_backend_ok(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_messages.forward_from_gajim") as mock_f:
            d._forward_natural_to_backend(_msg(), "hola")
        mock_f.assert_called_once()

    def test_replies_error_when_api_fails(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_messages.forward_from_gajim",
                   side_effect=RuntimeError("net")):
            d._forward_natural_to_backend(_msg(), "hola")
        d.send.assert_called_once()


class TestDispatchIntent:

    def test_query_intents_route_to_chat_query(self):
        d = _make_dispatcher()
        d._handle_chat_query = MagicMock()
        d._dispatch_intent({"intent": "scan_devices"}, _msg(), "x", "u1")
        assert d._handle_chat_query.call_args.kwargs["action"] == "scan_devices"

    def test_unknown_plugin_falls_back_to_not_understand(self):
        d = _make_dispatcher()
        d._reply = MagicMock()
        d._dispatch_intent({"intent": "inventado"}, _msg(), "x", "u1")
        d._reply.assert_called_once()


class TestInvokeInfoPlugin:

    @pytest.mark.parametrize("cmd_name, expected_arg", [
        ("acciones", "luz"),
        ("ayuda", ""),
    ])
    def test_passes_dispositivo_only_for_acciones_command(self, cmd_name, expected_arg):
        d = _make_dispatcher()
        d._reply = MagicMock()
        d._register_command_in_backend = MagicMock()
        plugin = MagicMock(return_value="info")
        d._bot.all_commands = {cmd_name: plugin}
        d._invoke_info_plugin(cmd_name, cmd_name, {"dispositivo": "luz"}, _msg(), "x", "u1")
        assert plugin.call_args[0][1] == expected_arg


class TestRunPluginAndScan:

    @pytest.mark.parametrize("plugin_result, expected_error", [
        ({"tipo": "ok"}, None),
        ({"tipo": "error", "mensaje": "boom"}, "boom"),
    ])
    def test_handle_scan_updates_backend(self, plugin_result, expected_error):
        d = _make_dispatcher()
        d._update_command_in_backend = MagicMock()
        d._bot.all_commands = {"scan_devices": MagicMock(return_value=plugin_result)}
        d._handle_scan_command(_msg(), "c1")
        assert d._update_command_in_backend.call_args.kwargs["error"] == expected_error


class TestHandleChatQuery:

    def test_registers_pending_and_updates_on_happy_path(self):
        d = _make_dispatcher()
        d._reply = MagicMock()
        d._update_command_in_backend = MagicMock()
        d._bot.all_commands = {"scan_devices": MagicMock(return_value={"tipo": "ok"})}
        with patch("plugins.dispatcher.dispatcher.resolve_sender", return_value="u1"), \
             patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_commands.register_pending_from_bot",
                   return_value={"command_id": "c1"}):
            d._handle_chat_query(_msg(), "x", action="scan_devices", command_name="scan_devices")
        d._update_command_in_backend.assert_called_once_with("c1", error=None, result_data={"tipo": "ok"})

class TestBackendCommands:

    def test_update_command_skips_api_when_offline(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=False), \
             patch("plugins.dispatcher.dispatcher.api_commands.patch_result") as mock_fn:
            d._update_command_in_backend("c1", error="boom")
        mock_fn.assert_not_called()

    def test_register_command_silences_api_exception(self):
        d = _make_dispatcher()
        with patch("plugins.dispatcher.dispatcher.is_backend_reachable", return_value=True), \
             patch("plugins.dispatcher.dispatcher.api_commands.register_from_bot",
                   side_effect=RuntimeError("boom")):
            d._register_command_in_backend(
                user_id="u1", device_id=None, action="ayuda",
                payload={}, error=None, message_id=None,
            )


class TestCallbackMessage:

    def test_unauthorized_or_empty_aborts_before_dispatch(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value=None)
        d._handle_structured_message = MagicMock()
        d.callback_message(_msg(body="hola"))
        d._handle_structured_message.assert_not_called()

        d._check_sender_access.reset_mock()
        d.callback_message(_msg(body="   "))
        d._check_sender_access.assert_not_called()

    def test_no_intent_forwards_to_backend(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value="u1")
        d._handle_structured_message = MagicMock(return_value=False)
        d._extract_natural_classified = MagicMock(return_value=(None, "hola"))
        d._forward_natural_to_backend = MagicMock()
        d._dispatch_intent = MagicMock()
        d.callback_message(_msg(body="hola"))
        d._forward_natural_to_backend.assert_called_once()
        d._dispatch_intent.assert_not_called()

    def test_intent_present_dispatches(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value="u1")
        d._handle_structured_message = MagicMock(return_value=False)
        d._extract_natural_classified = MagicMock(return_value=({"intent": "ayuda"}, "hola"))
        d._dispatch_intent = MagicMock()
        d.callback_message(_msg(body="hola"))
        d._dispatch_intent.assert_called_once()

    def test_correlation_id_is_stored_in_extras(self):
        d = _make_dispatcher()
        d._check_sender_access = MagicMock(return_value="u1")
        d._handle_structured_message = MagicMock(return_value=True)
        cid = str(uuid.uuid4())
        msg = _msg(body=f"{cid}|hola")
        d.callback_message(msg)
        assert msg.extras["correlation_id"] == cid

