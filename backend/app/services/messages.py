from fastapi import HTTPException
from app.core.db import supabase
from app.models import BotWebhookPayload
from app.services.xmpp import send_xmpp_message


async def handle_webhook(payload: BotWebhookPayload) -> None:
    message = _find_message(payload)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    _save_response(message["id"], payload.response)

    if message.get("command_id"):
        _mark_command_executed(message["command_id"])


def _find_message(payload: BotWebhookPayload) -> dict | None:
    body = payload.body
    # El bot devuelve "command_id|body_original", extraemos solo el body
    if "|" in body:
        _, body = body.split("|", 1)

    if payload.message_id:
        result = supabase.table("messages")\
            .select("*")\
            .eq("xmpp_message_id", payload.message_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
    else:
        result = supabase.table("messages")\
            .select("*")\
            .ilike("body", body)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()

    return result.data[0] if result.data else None


def _save_response(message_id: str, response: str) -> None:
    supabase.table("messages").update({
        "response": response
    }).eq("id", message_id).execute()


def _mark_command_executed(command_id: str) -> None:
    supabase.table("commands").update({
        "status": "executed",
        "executed_at": "now()"
    }).eq("id", command_id).execute()


async def process_message(body: str, user_id: str, jid: str, xmpp_password: str) -> dict:
    command_id = _create_command(user_id, body)
    xmpp_message_id = await send_xmpp_message(f"{command_id}|{body}", jid, xmpp_password)
    message = _create_message(user_id, command_id, xmpp_message_id, body)
    _mark_command_sent(command_id, xmpp_message_id)
    return message


def _create_command(user_id: str, body: str) -> str:
    result = supabase.table("commands").insert({
        "user_id": user_id,
        "device_id": None,
        "action": body,
        "status": "pending"
    }).execute()
    return result.data[0]["id"]


def _create_message(user_id: str, command_id: str, xmpp_message_id: str | None, body: str) -> dict:
    result = supabase.table("messages").insert({
        "from_user_id": user_id,
        "command_id": command_id,
        "xmpp_message_id": xmpp_message_id,
        "body": body,
        "response": None
    }).execute()
    return result.data[0]


def _mark_command_sent(command_id: str, xmpp_message_id: str | None) -> None:
    supabase.table("commands").update({
        "xmpp_message_id": xmpp_message_id,
        "status": "sent"
    }).eq("id", command_id).execute()


def get_user_messages(user_id: str) -> list:
    result = supabase.table("messages")\
        .select("*")\
        .eq("from_user_id", user_id)\
        .order("created_at", desc=True)\
        .execute()
    return result.data