import sys
from pathlib import Path
from unittest.mock import MagicMock

# ── sys.path ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "plugins" / "network-scanner"))

sys.modules.setdefault("scapy",             MagicMock())
sys.modules.setdefault("scapy.all",         MagicMock())
sys.modules.setdefault("netifaces",         MagicMock())
sys.modules.setdefault("mac_vendor_lookup", MagicMock())
sys.modules.setdefault("zeroconf",          MagicMock())
sys.modules.setdefault("tinytuya",          MagicMock())
sys.modules.setdefault("aiowebostv",        MagicMock())
sys.modules.setdefault("wakeonlan",         MagicMock())
