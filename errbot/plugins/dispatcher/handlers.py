import json


def handle_device_command(data: dict, msg, bot) -> None:
    """Maneja un comando JSON que viene del backend (botón en la app).
    El JSON ya trae device_id/action/payload validados por el backend."""
    result = _run_driver_command(
        bot, msg,
        data["device_id"], data["action"], data.get("payload", {}),
    )
    response = "Command executed" if result.get("ok") else f"Error: {result.get('error', 'unknown')}"
    bot.send(msg.frm, response)

    command_id = data.get("command_id")
    if command_id:
        bot._update_command_in_backend(command_id, error=result.get("error"))


def _run_driver_command(bot, msg, device_id: str, action: str, payload: dict) -> dict:
    """Llama al plugin `control_device` con el JSON estándar y devuelve el resultado (dict)."""
    args = json.dumps({
        "device_id": device_id,
        "action":    action,
        "payload":   payload,
    })
    method = bot._get_command_from_plugins("control_device")
    return method(msg, args)
