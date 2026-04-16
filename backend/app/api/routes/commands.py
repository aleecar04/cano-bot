from fastapi import APIRouter, Depends
from app.api.routes.messages import verify_webhook_secret
from app.services.messages import create_command_from_bot

router = APIRouter(prefix="/commands", tags=["commands"])

@router.post(
    "/from-bot",
    dependencies=[Depends(verify_webhook_secret)],
    responses={401: {"description": "Invalid webhook token"}},
)
def create_command_from_bot_endpoint(body: dict):
    return create_command_from_bot(body)