from unittest.mock import MagicMock

from plugins.dispatcher.handlers import handle_device_command


def _bot(command_result):
    bot = MagicMock()
    bot._get_command_from_plugins.return_value = lambda m, a: command_result
    return bot


class TestDispatcherHandlers:

    def test_handle_device_command_sends_success_reply_when_ok(self):
        bot = _bot({"ok": True})
        handle_device_command(
            {"device_id": "device_lampara", "action": "encender", "payload": {}},
            MagicMock(frm="anabel@xmpp.cano-app.com"),
            bot,
        )
        bot.send.assert_called_once()
        assert "ejecutada" in bot.send.call_args[0][1].lower()

    def test_handle_device_command_updates_backend_on_command_id(self):
        bot = _bot({"ok": True})
        handle_device_command(
            {"device_id": "device_lampara", "action": "encender", "command_id": "cmd_encender"},
            MagicMock(frm="anabel@xmpp.cano-app.com"),
            bot,
        )
        bot._update_command_in_backend.assert_called_once()
