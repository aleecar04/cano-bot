import ollama
import json
import logging
from plugins.bot_config import OLLAMA_HOST

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el clasificador de intents de Cano-bot, asistente domótico. Responde SOLO con JSON válido, sin texto extra.

IMPORTANTE: Ignora palabras al inicio como "oye", "tío", "venga", "a ver", "mira", "por favor". El nombre del dispositivo usa espacios normales, nunca guiones bajos.

Formatos de respuesta:
- Control sin valor: {"intent":"control_device","accion":"encender|apagar|mute|subir_volumen|bajar_volumen","dispositivo":"NOMBRE","payload":{}}
- Control con valor: {"intent":"control_device","accion":"brillo|temperatura_color|set_volumen","dispositivo":"NOMBRE","payload":{"valor":NUMERO}}
- Color: {"intent":"control_device","accion":"color_rgb","dispositivo":"NOMBRE","payload":{"color":"rojo|verde|azul|amarillo|naranja|morado|violeta|rosa|cyan|celeste|blanco"}}
- Otros: {"intent":"list_devices"} | {"intent":"scan_devices"} | {"intent":"saludo"} | {"intent":"mi_ip"} | {"intent":"unknown"}

Ejemplos:
"enciende la luz" → {"intent":"control_device","accion":"encender","dispositivo":"luz","payload":{}}
"apaga la tele" → {"intent":"control_device","accion":"apagar","dispositivo":"tele","payload":{}}
"oye enciende el salón" → {"intent":"control_device","accion":"encender","dispositivo":"salón","payload":{}}
"tío apaga la luz del salón" → {"intent":"control_device","accion":"apagar","dispositivo":"luz del salón","payload":{}}
"sube el volumen de la tele" → {"intent":"control_device","accion":"subir_volumen","dispositivo":"tele","payload":{}}
"silencia la tele" → {"intent":"control_device","accion":"mute","dispositivo":"tele","payload":{}}
"brillo al 70" → {"intent":"control_device","accion":"brillo","dispositivo":"luz","payload":{"valor":70}}
"brillo máximo" → {"intent":"control_device","accion":"brillo","dispositivo":"luz","payload":{"valor":100}}
"volumen a 50" → {"intent":"control_device","accion":"set_volumen","dispositivo":"tele","payload":{"valor":50}}
"temperatura a 3000" → {"intent":"control_device","accion":"temperatura_color","dispositivo":"luz","payload":{"valor":3000}}
"luz cálida" → {"intent":"control_device","accion":"temperatura_color","dispositivo":"luz","payload":{"valor":2700}}
"luz fría" → {"intent":"control_device","accion":"temperatura_color","dispositivo":"luz","payload":{"valor":6500}}
"pon la luz en rojo" → {"intent":"control_device","accion":"color_rgb","dispositivo":"luz","payload":{"color":"rojo"}}
"luz verde" → {"intent":"control_device","accion":"color_rgb","dispositivo":"luz","payload":{"color":"verde"}}
"pon el salón en azul" → {"intent":"control_device","accion":"color_rgb","dispositivo":"salón","payload":{"color":"azul"}}
"hola" → {"intent":"saludo"}
"lista mis dispositivos" → {"intent":"list_devices"}
"escanea la red" → {"intent":"scan_devices"}"""

client = ollama.Client(host=OLLAMA_HOST, timeout=30.0)


def classify_intent(texto: str) -> dict:
    try:
        response = client.chat(
            model="qwen2.5:3b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": texto}
            ],
            options={"temperature": 0.1},
        )
        raw = response["message"]["content"].strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"intent": "unknown"}
    except Exception as e:
        logger.error(f"Error classifying intent: {e}")
        return {"intent": "ollama_error"}