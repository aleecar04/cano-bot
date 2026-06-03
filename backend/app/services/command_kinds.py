SYSTEM_ACTIONS = frozenset({"scan_devices", "list_devices"})
INFO_ACTIONS   = frozenset({"saludo", "mi_ip", "ayuda", "acciones"})

PREFIX_ACTIONS = SYSTEM_ACTIONS | INFO_ACTIONS


def classify_action_type(action: str | None) -> str:
    """Devuelve 'system', 'info' o 'device' según la acción."""
    if action in SYSTEM_ACTIONS:
        return "system"
    if action in INFO_ACTIONS:
        return "info"
    return "device"


def lookup_prefix_command(body: str) -> dict | None:
    """Si el body es un '!comando' conocido (info o system), devuelve un
    intent_data sintético equivalente al que produciría Ollama. En caso
    contrario devuelve None y el body se reenvía tal cual al bot."""
    if not body.startswith("!"):
        return None
    rest = body[1:].strip()
    if not rest:
        return None
    head, _, tail = rest.partition(" ")
    if head not in PREFIX_ACTIONS:
        return None
    intent_data: dict = {"intent": head}
    if head == "acciones" and tail:
        intent_data["dispositivo"] = tail.strip()
    return intent_data
