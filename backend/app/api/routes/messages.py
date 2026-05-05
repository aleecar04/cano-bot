from fastapi import APIRouter, HTTPException, Header, Depends
from app.api.deps import CurrentUser
from app.core.config import settings
from app.models import BotWebhookPayload, MessageCreate, MessagePublic
from app.services.messages import get_user_messages, process_message, handle_webhook
from app.services.home import require_house
from typing import Annotated

router = APIRouter(prefix="/messages", tags=["messages"])

def verify_webhook_secret(x_webhook_token: str = Header(None)) -> None:
    if not x_webhook_token or x_webhook_token != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

@router.post("/webhook")
async def bot_webhook(payload: BotWebhookPayload, _: Annotated[None, Depends(verify_webhook_secret)]):
    handle_webhook(payload)
    return {"ok": True}

@router.post("/", response_model=MessagePublic)
async def send_message(message_in: MessageCreate, current_user: CurrentUser):
    try:
        require_house(current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return await process_message(
        body=message_in.body,
        user_id=current_user["id"],
        conversation_id=str(message_in.conversation_id) if message_in.conversation_id else None
    )

@router.get("/", response_model=list[MessagePublic])
def get_messages(current_user: CurrentUser):
    return get_user_messages(current_user["id"])