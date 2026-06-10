"""
Errbot plugin integration test configuration.

Uses errbot's real TestBot / testbot pytest fixture (from errbot.backends.test).
Heavy hardware/network deps are pre-mocked here before any plugin import happens.

The parent tests/conftest.py already mocks scapy, netifaces, etc. but this
conftest also ensures tinytuya/aiowebostv are mocked (used by drivers layer).
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Path going up 4 levels: file → integration → plugins → tests → errbot/
ROOT = Path(__file__).parent.parent.parent.parent

# Ensure project root is importable for `from plugins.X import Y` inside plugins
sys.path.insert(0, str(ROOT))

# Extra hardware / IoT deps that control.py may pull in transitively
sys.modules.setdefault("tinytuya",   MagicMock())
sys.modules.setdefault("aiowebostv", MagicMock())

# Re-export the testbot fixture so pytest discovers it for all tests in this directory.
# errbot.backends.test defines `testbot` as a pytest fixture.
from errbot.backends.test import testbot  # noqa: F401
