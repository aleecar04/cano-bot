import time
import logging
import requests
from plugins.bot_config import BACKEND_URL, AUTH_HEADERS

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 5

_backend_available: bool = True
_last_backend_check: float = 0.0
_BACKEND_CHECK_INTERVAL = 30.0


def is_backend_reachable() -> bool:
    global _backend_available, _last_backend_check
    now = time.monotonic()
    if now - _last_backend_check < _BACKEND_CHECK_INTERVAL:
        return _backend_available
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=3)
        _backend_available = r.status_code < 500
    except Exception:
        _backend_available = False
    _last_backend_check = now
    if not _backend_available:
        logger.warning("Backend unreachable")
    return _backend_available


def _request(method: str, path: str, *, timeout: float = _DEFAULT_TIMEOUT, **kwargs) -> requests.Response:
    headers = {**AUTH_HEADERS, **kwargs.pop("headers", {})}
    fn = getattr(requests, method.lower())
    r = fn(f"{BACKEND_URL}{path}", headers=headers, timeout=timeout, **kwargs)
    r.raise_for_status()
    return r


def get(path: str, **kwargs) -> requests.Response:
    return _request("GET", path, **kwargs)


def post(path: str, **kwargs) -> requests.Response:
    return _request("POST", path, **kwargs)


def patch(path: str, **kwargs) -> requests.Response:
    return _request("PATCH", path, **kwargs)
