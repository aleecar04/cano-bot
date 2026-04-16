import requests
import time
import logging
from plugins.bot_config import BACKEND_URL, WEBHOOK_HEADERS

logger = logging.getLogger(__name__)

_backend_available: bool = True
_last_backend_check: float = 0.0
_BACKEND_CHECK_INTERVAL = 30.0  # seconds between connectivity checks


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
        logger.warning("Backend unreachable — skipping webhook calls")
    return _backend_available


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

    def update_device_status(self, device_id: str, is_online: bool, estado: dict | None = None) -> None:
        if not is_backend_reachable():
            logger.info(f"[offline-log] device {device_id} online={is_online}")
            return
        try:
            r = requests.patch(
                f"{BACKEND_URL}/api/v1/devices/{device_id}/status",
                json={"is_online": is_online, "estado": estado or {}},
                headers=WEBHOOK_HEADERS,
                timeout=3,
            )
            r.raise_for_status()
        except requests.Timeout:
            logger.warning(f"Timeout updating status for {device_id}")
        except Exception as e:
            logger.error(f"Error updating device status: {e}")