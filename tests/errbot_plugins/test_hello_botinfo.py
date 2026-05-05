"""
Integration tests for Hello and BotInfo errbot plugins.
Uses errbot's TestBot fixture.
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).parent.parent.parent

# Both plugins are in separate directories; load them together
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


# ── Hello plugin ──────────────────────────────────────────────────────────────

class TestHelloPlugin:
    extra_plugin_dir = [
        str(ROOT / "plugins" / "hello"),
    ]

    def test_tryme_returns_works(self, testbot):
        testbot.push_message("!tryme")
        msg = testbot.pop_message()
        assert "works" in msg.lower()


# ── BotInfo plugin ────────────────────────────────────────────────────────────

class TestBotInfoPlugin:
    extra_plugin_dir = [
        str(ROOT / "plugins" / "bot-info"),
    ]

    def test_who_are_you_responds_to_greeting(self, testbot):
        # re_botcmd with prefixed=False → natural language trigger (no !)
        testbot.push_message("hola")
        msg = testbot.pop_message()
        assert "cano-bot" in msg.lower() or "asistente" in msg.lower()

    def test_who_are_you_responds_to_buenos(self, testbot):
        testbot.push_message("buenos días!")
        msg = testbot.pop_message()
        assert len(msg) > 0

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
