import json
import logging
from pywebpush import webpush, WebPushException
from app.core.config import settings
from app.core.db import supabase
from app.repositories.push import push_subscription_repository

logger = logging.getLogger(__name__)


def _remove_subscription(sub_id: str) -> None:
    supabase.table("push_subscriptions").delete().eq("id", sub_id).execute()


def _dispatch(sub: dict, payload: str) -> None:
    try:
        webpush(
            subscription_info={
                "endpoint": sub["endpoint"],
                "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_CONTACT_EMAIL}"},
        )
    except WebPushException as exc:
        logger.warning("Push failed sub=%s: %s", sub["id"], exc)
        if exc.response is not None and exc.response.status_code in (404, 410):
            _remove_subscription(sub["id"])
    except Exception as exc:
        logger.warning("Push error sub=%s: %s", sub["id"], exc)


class PushService:

    def send_push(self, user_id: str, title: str, body: str) -> None:
        """Envía una push a todas las subscriptions del usuario.
        Único uso: notificar el resultado de una tarea programada (éxito/fallo)."""
        if not settings.VAPID_PRIVATE_KEY:
            return
        payload = json.dumps({"title": title, "body": body})
        for sub in push_subscription_repository.find_by_user(user_id):
            _dispatch(sub, payload)

    def subscribe(self, user_id: str, endpoint: str, p256dh: str, auth: str) -> None:
        """Register a push subscription for a user (upsert by endpoint)."""
        supabase.table("push_subscriptions").upsert(
            {
                "user_id":  user_id,
                "endpoint": endpoint,
                "p256dh":   p256dh,
                "auth":     auth,
            },
            on_conflict="endpoint",
        ).execute()

    def unsubscribe(self, user_id: str, endpoint: str) -> None:
        """Remove a push subscription for a user by endpoint."""
        (
            supabase.table("push_subscriptions")
            .delete()
            .eq("user_id", user_id)
            .eq("endpoint", endpoint)
            .execute()
        )


push_service = PushService()
