import requests
import time
import logging
from plugins.bot_config import BACKEND_URL, WEBHOOK_HEADERS

logger = logging.getLogger(__name__)

_backend_available: bool = True
_backend_just_recovered: bool = False
_last_backend_check: float = 0.0
_BACKEND_CHECK_INTERVAL = 30.0  # seconds between connectivity checks


def is_backend_reachable() -> bool:
    global _backend_available, _backend_just_recovered, _last_backend_check
    now = time.monotonic()
    if now - _last_backend_check < _BACKEND_CHECK_INTERVAL:
        return _backend_available
    previous = _backend_available
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=3)
        _backend_available = r.status_code < 500
    except Exception:
        _backend_available = False
    _last_backend_check = now
    if not previous and _backend_available:
        _backend_just_recovered = True
        logger.info("Backend came back online — flagging for device reload")
    elif not _backend_available:
        logger.warning("Backend unreachable — skipping webhook calls")
    return _backend_available


def consume_backend_recovery() -> bool:
    """Returns True once when backend transitions from unreachable to reachable."""
    global _backend_just_recovered
    if _backend_just_recovered:
        _backend_just_recovered = False
        return True
    return False


class BasePlugin:
    def log_message(self, from_jid: str, body: str, response: str, message_id: str | None = None) -> None:
        if not is_backend_reachable():
            logger.info(f"[offline-log] {from_jid}: {body} -> {response}")
            return
        try:
            r = requests.post(
                f"{BACKEND_URL}/api/v1/messages/webhook",
                json={
                    "from_jid": from_jid,
                    "body": body,
                    "response": response,
                    "message_id": message_id,
                },
                headers=WEBHOOK_HEADERS,
                timeout=3,
            )
            r.raise_for_status()
        except requests.Timeout:
            logger.warning("Webhook timeout — message not recorded")
        except requests.HTTPError as e:
            logger.error(f"Webhook HTTP error {e.response.status_code}: {e.response.text[:200]}")
        except Exception as e:
            logger.error(f"Error calling webhook: {e}")

