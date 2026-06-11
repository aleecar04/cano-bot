from unittest.mock import patch

import pytest
import requests as requests_lib

import api._client as backend_client
from plugins._core import BasePlugin


@pytest.fixture(autouse=True)
def reset_backend_cache():
    backend_client._last_backend_check = 0.0
    backend_client._backend_available = True
    yield
    backend_client._last_backend_check = 0.0
    backend_client._backend_available = True


class TestCorePlugin:

    def _make_plugin(self):
        return BasePlugin()

    def test_skipped_when_backend_unreachable(self):
        with patch("plugins._core.is_backend_reachable", return_value=False), \
             patch("api.messages.log_webhook") as mock_log:
            self._make_plugin().log_message("anabel@xmpp.cano-app.com", "hola", "respuesta")
        mock_log.assert_not_called()

    def test_log_message_survives_webhook_timeout(self):
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("api.messages.log_webhook", side_effect=requests_lib.Timeout()):
            self._make_plugin().log_message("anabel@xmpp.cano-app.com", "hola", "respuesta")

