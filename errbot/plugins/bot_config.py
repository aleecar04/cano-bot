import os
from pathlib import Path
from dotenv import load_dotenv


_bot_env = Path(__file__).resolve().parent.parent.parent / ".bot.env"
if _bot_env.exists():
    load_dotenv(_bot_env, override=True)

BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
AUTH_HEADERS: dict = {"Authorization": f"Bearer {BOT_TOKEN}"}
