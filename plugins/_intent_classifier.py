import ollama
import json
import os

from dotenv import load_dotenv
load_dotenv()

SYSTEM_PROMPT = """
Eres el clasificador de intents de Cano-bot, un asistente de domótica.
El usuario habla español informal, con faltas y abreviaciones.
Tu ÚNICA tarea es clasificar el mensaje en uno de estos intents:

- scan_devices: quiere escanear o listar dispositivos de la red
- mi_ip: pregunta por su IP pública
- saludo: saluda o pregunta quién eres
- unknown: cualquier otra cosa

Responde SOLO con JSON así: {"intent": "nombre_del_intent"}
Sin explicaciones. Sin texto extra. Solo el JSON.
"""

client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

def classify_intent(texto: str) -> str:
    try:
        response = client.chat(
            model="qwen2.5:3b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": texto}
            ]
        )

        raw = response["message"]["content"].strip()
        data = json.loads(raw)
        return data.get("intent", "unknown")

    except json.JSONDecodeError:
        return "unknown"
    except Exception as e:
        print(f"Error clasificando intent: {e}")
        return "unknown"