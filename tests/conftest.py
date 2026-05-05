"""
Test configuration — mocks heavy hardware/network dependencies before any
plugin import so tests run without scapy, netifaces, tinytuya, etc. installed.

errbot IS installed (see requirements.txt) so it is NOT mocked here.
The errbot_plugins/ sub-package uses errbot's real TestBot fixture.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# ── sys.path ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
# "network-scanner" has a hyphen → add it directly so scanner_service is importable
sys.path.insert(0, str(ROOT / "plugins" / "network-scanner"))

# ── Network / hardware deps ───────────────────────────────────────────────────
sys.modules.setdefault("scapy",             MagicMock())
sys.modules.setdefault("scapy.all",         MagicMock())
sys.modules.setdefault("netifaces",         MagicMock())
sys.modules.setdefault("mac_vendor_lookup", MagicMock())
sys.modules.setdefault("zeroconf",          MagicMock())
sys.modules.setdefault("tinytuya",          MagicMock())
sys.modules.setdefault("aiowebostv",        MagicMock())

sys.modules.setdefault("ollama", MagicMock())

# ── Physical device drivers ───────────────────────────────────────────────────
sys.modules.setdefault("drivers", MagicMock())
