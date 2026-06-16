import time

_TTL_S = 90.0

_last_seen: dict[str, float] = {}


def mark_seen(house_id: str) -> None:
    _last_seen[house_id] = time.monotonic()


def is_online(house_id: str) -> bool:
    ts = _last_seen.get(house_id)
    return ts is not None and (time.monotonic() - ts) < _TTL_S
