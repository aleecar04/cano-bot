from fastapi import APIRouter, Depends
from app.api.deps import CurrentUser
from app.api.bot_auth import bot_auth
from app.models.messages import MessageCreate, MessagePublic
from app.models.xmpp import BotWebhookPayload, GajimMessagePayload
from app.services.messages import get_user_messages, process_message, process_gajim_message, handle_webhook
from app.services.home import require_house

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/webhook")
async def bot_webhook(payload: BotWebhookPayload, house: dict = Depends(bot_auth)):
    handle_webhook(payload, house["id"])
    return {"ok": True}


@router.post("/from-gajim")
async def from_gajim(payload: GajimMessagePayload, house: dict = Depends(bot_auth)):
    """El bot reenvía aquí los mensajes naturales que recibe directamente de un
    cliente XMPP (Gajim). El backend clasifica y orquesta el dispatch."""
    await process_gajim_message(payload.from_jid, payload.body, house["id"])
    return {"ok": True}

@router.post("/", response_model=MessagePublic)
async def send_message(message_in: MessageCreate, current_user: CurrentUser):
    require_house(current_user["id"])
    return await process_message(
        body=message_in.body,
        user_id=current_user["id"],
        conversation_id=str(message_in.conversation_id) if message_in.conversation_id else None
    )

@router.get("/", response_model=list[MessagePublic])
def get_messages(current_user: CurrentUser):
    return get_user_messages(current_user["id"])