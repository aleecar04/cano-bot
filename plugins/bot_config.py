import os
from pathlib import Path
from dotenv import load_dotenv

# Load bot-specific .env (never contains server secrets)
_bot_env = Path(__file__).resolve().parent.parent / ".bot.env"
if _bot_env.exists():
    load_dotenv(_bot_env, override=True)

BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
WEBHOOK_HEADERS: dict = {"X-Webhook-Token": WEBHOOK_SECRET}
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://194.164.164.171:11434")
SIMULATION_MODE: bool = os.getenv("SIMULATION_MODE", "false").lower() == "true"
SIM_PORT_START: int = int(os.getenv("SIM_PORT_START", "8181"))
SIM_PORT_END: int   = int(os.getenv("SIM_PORT_END", "8199"))
