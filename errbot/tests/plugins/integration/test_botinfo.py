"""
Integration tests for Hello and BotInfo errbot plugins.
Uses errbot's TestBot fixture.
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).parent.parent.parent.parent
extra_plugin_dir = [
    str(ROOT / "plugins" / "hello"),
    str(ROOT / "plugins" / "bot-info"),
]


def _make_response(text, status=200):
    m = MagicMock()
    m.status_code = status
    m.text = text
    m.strip = MagicMock(return_value=text.strip())
    m.raise_for_status = MagicMock()
    return m


class TestBotInfoPlugin:
    extra_plugin_dir = [
        str(ROOT / "plugins" / "bot-info"),
    ]

    def test_mi_ip_with_successful_request(self, testbot):
        with patch("requests.get", return_value=_make_response("1.2.3.4")):
            testbot.push_message("!mi_ip")
            msg = testbot.pop_message()
        assert "1.2.3.4" in msg

    def test_mi_ip_handles_error(self, testbot):
        with patch("requests.get", side_effect=Exception("timeout")):
            testbot.push_message("!mi_ip")
            msg = testbot.pop_message()
        assert "error" in msg.lower()
