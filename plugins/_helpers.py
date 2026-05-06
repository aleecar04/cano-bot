import logging
import time
import requests
from plugins.bot_config import BACKEND_URL, WEBHOOK_HEADERS

logger = logging.getLogger(__name__)

_JID_CACHE: dict[str, tuple[str, float]] = {}
_JID_TTL = 300.0  # seconds


def get_user_id_from_jid(jid: str) -> str:
    """Resolve an XMPP JID to the app user_id stored in the backend (cached 5 min)."""
    jid_bare = jid.split("/")[0]
    cached = _JID_CACHE.get(jid_bare)
    if cached and (time.monotonic() - cached[1]) < _JID_TTL:
        return cached[0]
    r = requests.get(
        f"{BACKEND_URL}/api/v1/users/by-jid/{jid_bare}",
        headers=WEBHOOK_HEADERS,
        timeout=5,
    )
    r.raise_for_status()
    user_id: str = r.json()["user_id"]
    _JID_CACHE[jid_bare] = (user_id, time.monotonic())
    return user_id


_MEMBER_CACHE: dict[str, tuple[bool, float]] = {}
_MEMBER_TTL = 120.0


def is_house_member(user_id: str) -> bool:
    """Check if user_id belongs to any house (cached 2 min). Fail-open if backend unreachable."""
    cached = _MEMBER_CACHE.get(user_id)
    if cached and (time.monotonic() - cached[1]) < _MEMBER_TTL:
        return cached[0]
    try:
        r = requests.get(
            f"{BACKEND_URL}/api/v1/houses/member-check",
            headers=WEBHOOK_HEADERS,
            params={"user_id": user_id},
            timeout=5,
        )
        result = r.json().get("is_member", True) if r.ok else True
    except Exception:
        result = True  # fail-open: don't block if backend is down
    _MEMBER_CACHE[user_id] = (result, time.monotonic())
    return result


def get_user_devices(user_id: str) -> list[dict]:
    """Return all devices for the house of the given user."""
    r = requests.get(
        f"{BACKEND_URL}/api/v1/devices/all",
        headers=WEBHOOK_HEADERS,
        params={"user_id": user_id},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()


def get_device(device_id: str, user_id: str) -> dict | None:
    """Return a single device, verifying it belongs to the given user."""
    devices = get_user_devices(user_id)
    return next((d for d in devices if d["id"] == device_id), None)


def buscar_dispositivo_por_nombre(nombre: str, user_id: str) -> dict | None:
    """Find the first device whose name contains the given string (case-insensitive)."""
    devices = get_user_devices(user_id)
    nombre_lower = nombre.lower()
    return next((d for d in devices if nombre_lower in d["name"].lower()), None)


_COLOR_HEX_MAP: dict[str, str] = {
    "rojo":     "#ff2020",
    "naranja":  "#ff6400",
    "amarillo": "#ffc800",
    "verde":    "#00c800",
    "cyan":     "#00c8ff",
    "azul":     "#0000ff",
    "morado":   "#8000c8",
    "violeta":  "#9400d3",
    "rosa":     "#ff1493",
    "blanco":   "#ffffff",
}


def calculate_expected_state(device: dict, accion: str, payload: dict) -> dict:
    """
    Predict the device state after executing an action.
    Used to optimistically update the cache without waiting for the next poll.
    """
    current_state = device.get("estado", {})
    new_state = current_state.copy()

    if accion == "encender":
        new_state["power"] = "on"
    elif accion == "apagar":
        new_state["power"] = "off"
    elif accion == "brillo":
        new_state["brightness"] = payload.get("valor", 100)
    elif accion == "temperatura_color":
        new_state["color_temp"] = payload.get("valor", 4000)
        new_state["work_mode"] = "white"
    elif accion == "color_rgb":
        color_name = payload.get("color", "")
        hex_color = _COLOR_HEX_MAP.get(color_name)
        if hex_color:
            new_state["color_hex"] = hex_color
        new_state["work_mode"] = "colour"
    elif accion == "subir_volumen":
        new_state["volume"] = min(100, new_state.get("volume", 50) + 5)
    elif accion == "bajar_volumen":
        new_state["volume"] = max(0, new_state.get("volume", 50) - 5)
    elif accion == "mute":
        new_state["muted"] = not new_state.get("muted", False)

    return new_state
