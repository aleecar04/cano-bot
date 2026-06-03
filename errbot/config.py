import hashlib
import logging
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# .env and .bot.env live at the project root (one level above errbot/)
ROOT_DIR = os.path.dirname(BASE_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))
# Bot-specific vars override (created by setup-bot.sh, never contains server secrets)
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

# Cuenta XMPP compartida por TODOS los bots (BOT_USERNAME/BOT_PASSWORD); cada casa se
# distingue por el resource, derivado del hash del bot_token (el backend calcula el mismo
# valor desde bot_token_hash, así coinciden sin compartir más datos).
_BOT_TOKEN = os.getenv("BOT_TOKEN", "")
_SHARED_JID = os.getenv("BOT_USERNAME", "")
_SHARED_PASSWORD = os.getenv("BOT_PASSWORD", "")
_resource = "bot-" + hashlib.sha256(_BOT_TOKEN.encode()).hexdigest()[:12] if _BOT_TOKEN else "bot-default"

BOT_IDENTITY = {
    'username': f"{_SHARED_JID}/{_resource}" if _SHARED_JID else None,
    'password': _SHARED_PASSWORD,
}
