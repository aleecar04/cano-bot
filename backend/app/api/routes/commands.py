from typing import Annotated

from fastapi import APIRouter, Depends
from app.api.deps import CurrentUser
from app.api.bot_auth import bot_auth
from app.models.commands import CommandRequest
from app.services.commands import commands_service
from app.services.command_executor import execute_command, CommandSource

router = APIRouter(prefix="/commands", tags=["commands"])

BotHouse = Annotated[dict, Depends(bot_auth)]


@router.post("")
async def create_command(body: CommandRequest, current_user: CurrentUser):
    return await execute_command(
        action=body.action,
        payload=body.payload,
        user_id=current_user["id"],
        source=CommandSource(source_type="direct"),
        device_id=str(body.device_id) if body.device_id else None,
    )


@router.post("/from-bot", responses={401: {"description": "Invalid bot token"}})
def create_command_from_bot_endpoint(body: dict, house: BotHouse):
    body["_authenticated_house_id"] = house["id"]
    return commands_service.create_command_from_bot(body)


@router.patch("/{command_id}", responses={401: {"description": "Invalid bot token"}})
def update_command_endpoint(command_id: str, body: dict, house: BotHouse):
    commands_service.update_command_result(command_id, house["id"], body.get("error"), body.get("result_data"))
    return {"ok": True}
