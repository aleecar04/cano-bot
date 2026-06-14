from fastapi import APIRouter
from app.api.deps import CurrentUser
from app.core.config import settings
from app.models.push import PushSubscriptionBody
from app.services.push import push_service

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-public-key")
def get_vapid_public_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe", status_code=201)
def subscribe(body: PushSubscriptionBody, current_user: CurrentUser):
    push_service.subscribe(current_user["id"], body.endpoint, body.p256dh, body.auth)
    return {"ok": True}


@router.delete("/subscribe")
def unsubscribe(body: PushSubscriptionBody, current_user: CurrentUser):
    push_service.unsubscribe(current_user["id"], body.endpoint)
    return {"ok": True}
