
def _summarize_scan(data: dict) -> str:
    n = len(data.get("dispositivos", []))
    plural = "s" if n != 1 else ""
    return f"Encontré {n} dispositivo{plural} en tu red, te los detallo:"


def _summarize_device_list(data: dict) -> str:
    n = len(data.get("dispositivos", []))
    plural = "s" if n != 1 else ""
    return f"Tienes {n} dispositivo{plural} vinculado{plural}:"


_RESPONSE_BUILDERS = {
    "scan":         _summarize_scan,
    "list_devices": _summarize_device_list,
}


def format_command_response(action: str, data: dict, device_name: str, ok: bool, error: str | None) -> str:
    if not ok:
        if error:
            return error  # error humano (lo pasa quien llama); el técnico va a commands.error
        return f"No pude completar la acción sobre {device_name}." if device_name else "No se pudo completar la operación."
    builder = _RESPONSE_BUILDERS.get(action)
    if builder:
        return builder(data or {})
    return f"{device_name}: {action} ejecutado."
