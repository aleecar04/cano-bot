"""
Conftest específico para tests de drivers.
Mockea dependencias de hardware pero NO el paquete drivers completo,
para que los tests puedan importar las clases reales.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

# Mock hardware/network deps before any driver import
for mod in ("tinytuya", "aiowebostv", "wakeonlan", "samsungtvws",
            "scapy", "scapy.all", "netifaces", "mac_vendor_lookup", "zeroconf"):
    sys.modules.setdefault(mod, MagicMock())

# Remove the top-level mock of 'drivers' if it was set by the parent conftest,
# so this subdirectory can import the real driver classes
if "drivers" in sys.modules and isinstance(sys.modules["drivers"], MagicMock):
    del sys.modules["drivers"]
for key in list(sys.modules):
    if key.startswith("drivers.") and isinstance(sys.modules[key], MagicMock):
        del sys.modules[key]
