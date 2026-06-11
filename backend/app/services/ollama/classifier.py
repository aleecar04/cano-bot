import json
import logging
import ollama

from app.core.config import settings
from app.services.ollama.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_async_client = ollama.AsyncClient(host=settings.OLLAMA_HOST, timeout=30.0)


async def classify_intent(texto: str) -> dict:
    try:
        response = await _async_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": texto},
            ],
            options={"temperature": 0.1},
            keep_alive="30m",
        )
        return json.loads(response["message"]["content"].strip())
    except json.JSONDecodeError:
        return {"intent": "unknown"}
    except Exception:
        logger.exception("Ollama classifier failed")
        return {"intent": "ollama_error"}
