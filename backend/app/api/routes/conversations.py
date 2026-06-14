from fastapi import APIRouter
from app.api.deps import CurrentUser
from app.core.errors import forbidden
from app.models.conversations import ConversationCreate, ConversationPublic
from app.services.messages import messages_service

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.post("/", response_model=ConversationPublic)
def new_conversation(current_user: CurrentUser, body: ConversationCreate):
    title = body.title or "Nueva conversación"
    return messages_service.create_conversation(current_user["id"], title=title)

@router.get("/", response_model=list[ConversationPublic])
def list_conversations(current_user: CurrentUser):
    return messages_service.get_user_conversations(current_user["id"])

@router.get("/{conversation_id}/messages")
def conversation_messages(conversation_id: str, current_user: CurrentUser):
    convs = messages_service.get_user_conversations(current_user["id"])
    if not any(str(c["id"]) == conversation_id for c in convs):
        raise forbidden("No tienes acceso a esta conversación")
    return messages_service.get_conversation_messages(conversation_id)
