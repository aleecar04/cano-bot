import hashlib
import logging
import os
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))
_bot_env = os.path.join(ROOT_DIR, ".bot.env")
if os.path.exists(_bot_env):
    load_dotenv(_bot_env, override=True)

BACKEND = "XMPP"
BOT_LOG_LEVEL = logging.INFO
XMPP_KEEPALIVE_INTERVAL = 0.5
BOT_DATA_DIR = os.path.join(BASE_DIR, "data")
BOT_EXTRA_PLUGIN_DIR = os.path.join(BASE_DIR, "plugins")
BOT_EXTRA_BACKEND_DIR = os.path.join(BASE_DIR, "backend-plugins")
BOT_LOG_FILE = os.path.join(BASE_DIR, "errbot.log")
BOT_ADMINS = (
    "aleecr04@xmpp.aleecr.es",
)


_BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
_BACKEND_URL = os.getenv("BACKEND_URL", "")
_resource = "bot-" + hashlib.sha256(_BOT_TOKEN.encode()).hexdigest()[:12] if _BOT_TOKEN else "bot-default"


def _fetch_xmpp_credentials() -> tuple[str, str]:
    """Solicita al backend credenciales XMPP efimeras de un solo uso."""
    if not _BOT_TOKEN or not _BACKEND_URL:
        raise RuntimeError("Faltan BOT_TOKEN o BACKEND_URL en el .env del bot")
    res = requests.post(
        f"{_BACKEND_URL.rstrip('/')}/api/v1/bot/xmpp-token",
        headers={"Authorization": f"Bearer {_BOT_TOKEN}"},
        timeout=10,
    )
    res.raise_for_status()
    data = res.json()
    return data["username"], data["password"]


_SHARED_JID, _SHARED_PASSWORD = _fetch_xmpp_credentials()

BOT_IDENTITY = {
    'username': f"{_SHARED_JID}/{_resource}",
    'password': _SHARED_PASSWORD,
}
