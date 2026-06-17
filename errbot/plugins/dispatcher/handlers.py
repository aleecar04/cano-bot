import json


def handle_device_command(data: dict, msg, bot) -> None:
    result = _run_driver_command(
        bot, msg,
        data["device_id"], data["action"], data.get("payload", {}),
    )
    ok = result.get("ok")
    response = "Acción ejecutada correctamente" if ok else f"No se pudo completar: {result.get('error', 'error desconocido')}"
    bot.send(msg.frm, response)

    command_id = data.get("command_id")
    if command_id:
        bot._update_command_in_backend(command_id, error=result.get("error"), response=response)


def _run_driver_command(bot, msg, device_id: str, action: str, payload: dict) -> dict:
    args = json.dumps({
        "device_id": device_id,
        "action":    action,
        "payload":   payload,
    })
    method = bot._get_command_from_plugins("control_device")
    return method(msg, args)
