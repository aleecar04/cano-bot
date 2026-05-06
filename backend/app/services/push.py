import json
import logging
from pywebpush import webpush, WebPushException
from app.core.config import settings
from app.core.db import supabase

logger = logging.getLogger(__name__)


def _get_subscriptions(user_id: str) -> list[dict]:
    result = (
        supabase.table("push_subscriptions")
        .select("id, endpoint, p256dh, auth")
        .eq("user_id", user_id)
        .execute()
    )
    return result.data or []


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


def send_push(user_id: str, title: str, body: str) -> None:
    """Send a push notification to all subscriptions of a user."""
    if not settings.VAPID_PRIVATE_KEY:
        return
    payload = json.dumps({"title": title, "body": body})
    for sub in _get_subscriptions(user_id):
        _dispatch(sub, payload)


def send_push_to_house_owners(house_id: str, title: str, body: str) -> None:
    result = (
        supabase.table("house_members")
        .select("user_id")
        .eq("house_id", house_id)
        .eq("role", "owner")
        .execute()
    )
    for m in result.data or []:
        send_push(m["user_id"], title, body)


def send_push_to_all_owners(title: str, body: str) -> None:
    """Notify every house owner — used for bot-down alerts."""
    result = (
        supabase.table("house_members")
        .select("user_id")
        .eq("role", "owner")
        .execute()
    )
    for m in result.data or []:
        send_push(m["user_id"], title, body)
