import ollama
import json
import logging
from plugins.bot_config import OLLAMA_HOST

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres el clasificador de intents de Cano-bot, asistente de domotica.
El usuario habla español informal, con faltas y abreviaciones.
Responde SOLO con JSON. Sin texto extra.

Para controlar dispositivos:
{"intent": "control_device", "accion": "encender|apagar|brillo|subir_volumen|bajar_volumen|mute", "dispositivo": "nombre del dispositivo"}

Para listar dispositivos:
{"intent": "list_devices"}

Para escanear la red:
{"intent": "scan_devices"}

Para saludo o preguntar quien eres:
{"intent": "saludo"}

Para preguntar la IP:
{"intent": "mi_ip"}

Cualquier otra cosa:
{"intent": "unknown"}
"""

client = ollama.Client(host=OLLAMA_HOST)


def classify_intent(texto: str) -> dict:
    try:
        response = client.chat(
            model="qwen2.5:3b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": texto}
            ]
        )
        raw = response["message"]["content"].strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"intent": "unknown"}
    except Exception as e:
        logger.error(f"Error classifying intent: {e}")
        return {"intent": "unknown"}