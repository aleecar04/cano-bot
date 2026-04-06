from fastapi import APIRouter, HTTPException, Header, Depends
from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.db import supabase
from app.models import BotWebhookPayload, MessageCreate, MessagePublic
from app.services.messages import get_user_messages, process_message, handle_webhook

router = APIRouter(prefix="/messages", tags=["messages"])


def verify_webhook_secret(x_webhook_token: str = Header(None)) -> None:
    if not x_webhook_token or x_webhook_token != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook token")


@router.post("/webhook")
async def bot_webhook(payload: BotWebhookPayload, _: None = Depends(verify_webhook_secret)):
    await handle_webhook(payload)
    return {"ok": True}


@router.post("/", response_model=MessagePublic)
async def send_message(message_in: MessageCreate, current_user: CurrentUser):
    result = supabase.table("base_user").select("jid, xmpp_password").eq("id", current_user["id"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User XMPP account not found")
    base_user = result.data[0]

    return await process_message(
        body=message_in.body,
        user_id=current_user["id"],
        jid=base_user["jid"],
        xmpp_password=base_user["xmpp_password"]
    )


@router.get("/", response_model=list[MessagePublic])
def get_messages(current_user: CurrentUser):
    return get_user_messages(current_user["id"])