import logging
import time
import unicodedata
from api import users as api_users, devices as api_devices

logger = logging.getLogger(__name__)

_JID_CACHE: dict[str, tuple[str | None, float]] = {}
_JID_TTL = 300.0  # seconds


def resolve_sender(jid: str) -> str | None:
    jid_bare = jid.split("/")[0]
    cached = _JID_CACHE.get(jid_bare)
    if cached and (time.monotonic() - cached[1]) < _JID_TTL:
        return cached[0]
    user_id = api_users.resolve_in_house(jid_bare)
    _JID_CACHE[jid_bare] = (user_id, time.monotonic())
    return user_id


def get_device(device_id: str) -> dict | None:
    return next((d for d in api_devices.get_all() if d["id"] == device_id), None)


_DEVICE_STOPWORDS = {"el", "la", "los", "las", "del", "de", "en", "mi", "mis", "un", "una"}


def _normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()
    return " ".join(s.split())


def find_device_by_name(name: str) -> dict | None:
    devices = api_devices.get_all()
    q = _normalize_text(name)
    if not q:
        return None
    for d in devices:
        n = _normalize_text(d["name"])
        if q in n or n in q:
            return d
    q_tokens = {t for t in q.split() if t not in _DEVICE_STOPWORDS}
    best, best_score = None, 0
    for d in devices:
        n_tokens = {t for t in _normalize_text(d["name"]).split() if t not in _DEVICE_STOPWORDS}
        score = len(q_tokens & n_tokens)
        if score > best_score:
            best, best_score = d, score
    return best if best_score > 0 else None


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


def calculate_expected_state(device: dict, action: str, payload: dict) -> dict:
    current_state = device.get("state", {})
    new_state = current_state.copy()

    if action == "encender":
        new_state["power"] = "on"
    elif action == "apagar":
        new_state["power"] = "off"
    elif action == "brillo":
        new_state["brightness"] = payload.get("value", 100)
    elif action == "temperatura_color":
        new_state["color_temp"] = payload.get("value", 4000)
        new_state["work_mode"] = "white"
    elif action == "color_rgb":
        color_name = payload.get("color", "")
        hex_color = _COLOR_HEX_MAP.get(color_name)
        if hex_color:
            new_state["color_hex"] = hex_color
        new_state["work_mode"] = "colour"
    elif action == "subir_volumen":
        new_state["volume"] = min(100, new_state.get("volume", 50) + 5)
    elif action == "bajar_volumen":
        new_state["volume"] = max(0, new_state.get("volume", 50) - 5)
    elif action == "mute":
        new_state["volume"] = 0
    elif action == "set_volumen":
        new_state["volume"] = max(0, min(100, int(payload.get("value", 50))))

    return new_state
