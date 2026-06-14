from typing import Annotated

from fastapi import APIRouter, Depends
from app.api.deps import CurrentUser
from app.api.bot_auth import bot_auth
from app.models.messages import MessageCreate, MessagePublic
from app.models.xmpp import BotWebhookPayload, GajimMessagePayload
from app.services.messages import messages_service
from app.services.home import home_service

router = APIRouter(prefix="/messages", tags=["messages"])

BotHouse = Annotated[dict, Depends(bot_auth)]


@router.post("/webhook")
async def bot_webhook(payload: BotWebhookPayload, house: BotHouse):
    messages_service.handle_webhook(payload, house["id"])
    return {"ok": True}


@router.post("/from-gajim")
async def from_gajim(payload: GajimMessagePayload, house: BotHouse):
    await messages_service.process_gajim_message(payload.from_jid, payload.body, house["id"])
    return {"ok": True}

@router.post("/", response_model=MessagePublic)
async def send_message(message_in: MessageCreate, current_user: CurrentUser):
    home_service.require_house(current_user["id"])
    return await messages_service.process_message(
        body=message_in.body,
        user_id=current_user["id"],
        conversation_id=str(message_in.conversation_id) if message_in.conversation_id else None
    )

@router.get("/", response_model=list[MessagePublic])
def get_messages(current_user: CurrentUser):
    return messages_service.get_user_messages(current_user["id"])
