import logging
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BACKEND = "XMPP"
BOT_DATA_DIR = os.path.join(BASE_DIR, "data")
BOT_EXTRA_PLUGIN_DIR = os.path.join(BASE_DIR, "plugins")
BOT_EXTRA_BACKEND_DIR = os.path.join(BASE_DIR, "backend-plugins")
BOT_LOG_FILE = os.path.join(BASE_DIR, "errbot.log")
BOT_LOG_LEVEL = logging.INFO
BOT_ADMINS = (
    "tu-usuario@tu-servidor-xmpp.com",
)
BOT_IDENTITY = {
    'username': os.getenv("BOT_USERNAME"),
    'password': os.getenv("BOT_PASSWORD"),
}