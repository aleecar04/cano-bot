from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.deps import CurrentUser
from app.api.routes.messages import verify_webhook_secret
from app.core.config import settings
from app.core.db import supabase

router = APIRouter(prefix="/push", tags=["push"])


class PushSubscriptionBody(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.get("/vapid-public-key")
def get_vapid_public_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe", status_code=201)
def subscribe(body: PushSubscriptionBody, current_user: CurrentUser):
    """Register a browser push subscription for the current user."""
    supabase.table("push_subscriptions").upsert(
        {
            "user_id":  current_user["id"],
            "endpoint": body.endpoint,
            "p256dh":   body.p256dh,
            "auth":     body.auth,
        },
        on_conflict="endpoint",
    ).execute()
    return {"ok": True}


@router.delete("/subscribe")
def unsubscribe(body: PushSubscriptionBody, current_user: CurrentUser):
    """Remove a push subscription."""
    supabase.table("push_subscriptions").delete().eq(
        "user_id", current_user["id"]
    ).eq("endpoint", body.endpoint).execute()
    return {"ok": True}


@router.post("/bot-down", dependencies=[Depends(verify_webhook_secret)])
def bot_down():
    """Called by the bot on shutdown. Notifies all house owners."""
    from app.services.push import send_push_to_all_owners
    send_push_to_all_owners(
        "🤖 Asistente desconectado",
        "El bot no está disponible temporalmente. Los comandos de voz no funcionarán hasta que vuelva.",
    )
    return {"ok": True}
