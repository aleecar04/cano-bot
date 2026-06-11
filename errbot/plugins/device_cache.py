import time
from dataclasses import dataclass


@dataclass
class DeviceState:
    state: dict
    is_online: bool
    last_update: float


class DeviceStateCache:

    def __init__(self):
        self._devices: dict[str, DeviceState] = {}

    def get(self, device_id: str) -> DeviceState | None:
        return self._devices.get(device_id)

    def update(self, device_id: str, state: dict, is_online: bool) -> DeviceState:
        cached = DeviceState(state=state, is_online=is_online, last_update=time.time())
        self._devices[device_id] = cached
        return cached

    def mark_offline(self, device_id: str) -> None:
        if device_id in self._devices:
            self._devices[device_id].is_online = False


device_cache = DeviceStateCache()
