import logging
import requests
from api import is_backend_reachable
from api import messages as api_messages

logger = logging.getLogger(__name__)


class BasePlugin:
    def log_message(self, from_jid: str, body: str, response: str, message_id: str | None = None) -> None:
        if not is_backend_reachable():
            logger.info(f"[offline-log] {from_jid}: {body} -> {response}")
            return
        try:
            api_messages.log_webhook(from_jid, body, response, message_id)
        except requests.Timeout:
            logger.warning("Webhook timeout — message not recorded")
        except requests.HTTPError as e:
            logger.error(f"Webhook HTTP error {e.response.status_code}: {e.response.text[:200]}")
        except Exception as e:
            logger.error(f"Error calling webhook: {e}")
