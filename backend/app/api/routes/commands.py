from fastapi import APIRouter, Depends
from app.api.routes.messages import verify_webhook_secret
from app.services.messages import create_command_from_bot, update_command_result

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post(
    "/from-bot",
    dependencies=[Depends(verify_webhook_secret)],
    responses={401: {"description": "Invalid webhook token"}},
)
def create_command_from_bot_endpoint(body: dict):
    """Bot uses this to register conversation (natural language) commands."""
    return create_command_from_bot(body)


@router.patch(
    "/{command_id}",
    dependencies=[Depends(verify_webhook_secret)],
    responses={401: {"description": "Invalid webhook token"}},
)
def update_command_endpoint(command_id: str, body: dict):
    """Bot calls this to mark a pending command as executed or failed."""
    update_command_result(command_id, body.get("error"))
    return {"ok": True}