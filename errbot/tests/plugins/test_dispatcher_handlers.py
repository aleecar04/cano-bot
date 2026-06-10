from unittest.mock import MagicMock


def _bot(command_result):
    bot = MagicMock()
    bot._get_command_from_plugins.return_value = lambda m, a: command_result
    return bot


def test_handle_device_command_sends_success_reply_when_ok():
    from plugins.dispatcher.handlers import handle_device_command
    bot = _bot({"ok": True})
    handle_device_command(
        {"device_id": "d1", "action": "encender", "payload": {}},
        MagicMock(frm="alice@x"),
        bot,
    )
    bot.send.assert_called_once()
    assert "executed" in bot.send.call_args[0][1].lower()


def test_handle_device_command_sends_error_reply():
    from plugins.dispatcher.handlers import handle_device_command
    bot = _bot({"ok": False, "error": "timeout"})
    handle_device_command(
        {"device_id": "d1", "action": "encender", "payload": {}},
        MagicMock(frm="alice@x"),
        bot,
    )
    assert "timeout" in bot.send.call_args[0][1]


def test_handle_device_command_updates_backend_on_command_id():
    from plugins.dispatcher.handlers import handle_device_command
    bot = _bot({"ok": True})
    handle_device_command(
        {"device_id": "d1", "action": "encender", "command_id": "c-1"},
        MagicMock(frm="alice@x"),
        bot,
    )
    bot._update_command_in_backend.assert_called_once()


