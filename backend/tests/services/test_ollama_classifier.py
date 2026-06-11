import asyncio
import json
from unittest.mock import AsyncMock, patch

from app.services.ollama.classifier import classify_intent


def _run(coro):
    return asyncio.run(coro)


class TestOllamaClassifier:

    def test_valid_response_returns_dict(self):
        with patch("app.services.ollama.classifier._async_client") as mock_client:
            mock_client.chat = AsyncMock(return_value={
                "message": {"content": json.dumps({"intent": "control_device", "accion": "encender"})}
            })
            result = _run(classify_intent("enciende la luz"))
        assert result == {"intent": "control_device", "accion": "encender"}

    def test_unknown_if_bad_format(self):
        with patch("app.services.ollama.classifier._async_client") as mock_client:
            mock_client.chat = AsyncMock(return_value={
                "message": {"content": "esto-no-es-json"}
            })
            result = _run(classify_intent("hola"))
        assert result == {"intent": "unknown"}

    def test_ollama_error(self):
        with patch("app.services.ollama.classifier._async_client") as mock_client:
            mock_client.chat = AsyncMock(side_effect=ConnectionError("no ollama"))
            result = _run(classify_intent("hola"))
        assert result == {"intent": "ollama_error"}
