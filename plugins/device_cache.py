import time
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class DeviceState:
    device_id: str
    estado: dict
    is_online: bool
    last_update: float
    source: str
    confidence: float = 1.0

    def is_stale(self, timeout: int = 60) -> bool:
        return (time.time() - self.last_update) > timeout

    def age_seconds(self) -> int:
        return int(time.time() - self.last_update)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["last_update_iso"] = datetime.fromtimestamp(self.last_update).isoformat()
        d["age_seconds"] = self.age_seconds()
        return d


class DeviceStateCache:
    def __init__(self):
        self.devices: Dict[str, DeviceState] = {}

    def get(self, device_id: str) -> Optional[DeviceState]:
        """Obtiene el estado actual de un dispositivo"""
        return self.devices.get(device_id)

    def get_all(self) -> Dict[str, DeviceState]:
        """Obtiene todos los dispositivos en caché"""
        return self.devices.copy()

    def update(
        self,
        device_id: str,
        estado: dict,
        is_online: bool,
        source: str = "unknown",
        confidence: float = 1.0,
    ) -> DeviceState:
        device_state = DeviceState(
            device_id=device_id,
            estado=estado,
            is_online=is_online,
            last_update=time.time(),
            source=source,
            confidence=confidence,
        )
        self.devices[device_id] = device_state
        return device_state

    def mark_stale(self, device_id: str):
        """Marca un dispositivo como posiblemente desactualizado"""
        if device_id in self.devices:
            self.devices[device_id].confidence = 0.3

    def mark_offline(self, device_id: str):
        """Marca un dispositivo como offline"""
        if device_id in self.devices:
            self.devices[device_id].is_online = False
            self.devices[device_id].confidence = 0.8

    def clear(self, device_id: str = None):
        """Limpia la caché de un dispositivo o todo"""
        if device_id:
            self.devices.pop(device_id, None)
        else:
            self.devices.clear()

    def get_stale_devices(self, timeout: int = 60) -> Dict[str, DeviceState]:
        """Retorna dispositivos cuyo estado está desactualizado"""
        return {
            device_id: state
            for device_id, state in self.devices.items()
            if state.is_stale(timeout)
        }

    def get_status_summary(self) -> dict:
        """Resumen del estado de la caché para logging"""
        total = len(self.devices)
        online = sum(1 for s in self.devices.values() if s.is_online)
        stale = len(self.get_stale_devices())
        return {
            "total_cached": total,
            "online": online,
            "offline": total - online,
            "stale": stale,
            "last_update": max(
                (s.last_update for s in self.devices.values()), default=0
            ),
        }


device_cache = DeviceStateCache()
