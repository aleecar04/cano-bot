from unittest.mock import MagicMock


class TestHandleDeviceCommand:

    def test_ejecuta_y_envía_respuesta_de_éxito(self):
        from plugins.dispatcher.handlers import handle_device_command
        bot = MagicMock()
        bot._get_command_from_plugins.return_value = lambda m, a: {"ok": True}
        msg = MagicMock(frm="alice@x")
        handle_device_command(
            {"device_id": "d1", "action": "encender", "payload": {}}, msg, bot
        )
        bot.send.assert_called_once()
        assert "executed" in bot.send.call_args[0][1].lower()

    def test_envía_error_si_no_ok(self):
        from plugins.dispatcher.handlers import handle_device_command
        bot = MagicMock()
        bot._get_command_from_plugins.return_value = lambda m, a: {"ok": False, "error": "timeout"}
        msg = MagicMock(frm="alice@x")
        handle_device_command(
            {"device_id": "d1", "action": "encender", "payload": {}}, msg, bot
        )
        sent = bot.send.call_args[0][1]
        assert "timeout" in sent

    def test_actualiza_comando_si_viene_command_id(self):
        from plugins.dispatcher.handlers import handle_device_command
        bot = MagicMock()
        bot._get_command_from_plugins.return_value = lambda m, a: {"ok": True}
        msg = MagicMock(frm="alice@x")
        handle_device_command(
            {"device_id": "d1", "action": "encender", "command_id": "c-1"}, msg, bot
        )
        bot._update_command_in_backend.assert_called_once()
