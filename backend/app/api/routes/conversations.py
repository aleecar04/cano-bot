from fastapi import APIRouter
from app.api.deps import CurrentUser
from app.models import ConversationPublic
from app.services.messages import (
    create_conversation,
    get_user_conversations,
    get_conversation_messages,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.post("/", response_model=ConversationPublic)
def new_conversation(current_user: CurrentUser):
    return create_conversation(current_user["id"])

@router.get("/", response_model=list[ConversationPublic])
def list_conversations(current_user: CurrentUser):
    return get_user_conversations(current_user["id"])

@router.get("/{conversation_id}/messages")
def conversation_messages(conversation_id: str, current_user: CurrentUser):
    return get_conversation_messages(conversation_id)