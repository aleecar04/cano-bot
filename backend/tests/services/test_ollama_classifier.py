from unittest.mock import AsyncMock, patch
import asyncio
import json

from app.services.ollama.classifier import classify_intent


def _run(coro):
    return asyncio.run(coro)


class TestClassifyIntent:

    def test_respuesta_valida_devuelve_dict(self):
        with patch("app.services.ollama.classifier._async_client") as mock_client:
            mock_client.chat = AsyncMock(return_value={
                "message": {"content": json.dumps({"intent": "control_device", "accion": "encender"})}
            })
            result = _run(classify_intent("enciende la luz"))
        assert result == {"intent": "control_device", "accion": "encender"}

    def test_json_invalido_devuelve_unknown(self):
        with patch("app.services.ollama.classifier._async_client") as mock_client:
            mock_client.chat = AsyncMock(return_value={
                "message": {"content": "esto-no-es-json"}
            })
            result = _run(classify_intent("hola"))
        assert result == {"intent": "unknown"}

    def test_excepcion_de_ollama_devuelve_ollama_error(self):
        with patch("app.services.ollama.classifier._async_client") as mock_client:
            mock_client.chat = AsyncMock(side_effect=ConnectionError("no ollama"))
            result = _run(classify_intent("hola"))
        assert result == {"intent": "ollama_error"}
