from fastapi import HTTPException
from app.core.db import supabase
from app.models import BotWebhookPayload
from app.services.xmpp import send_xmpp_message
from app.core.config import settings

async def process_message(body: str, user_id: str, conversation_id: str | None) -> dict:
    import httpx as _httpx
    xmpp_account = _get_base_user(user_id)
    if conversation_id:
        _verify_conversation(conversation_id, user_id)

    try:
        xmpp_message_id = await send_xmpp_message(
            body,
            xmpp_account["jid"],
            xmpp_account["password"]
        )
    except _httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error enviando mensaje XMPP: {e.response.status_code} {e.response.text[:200]}"
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Servicio XMPP no disponible: {e}")

    message = _create_message(user_id, None, xmpp_message_id, body, conversation_id)

    if conversation_id:
        _touch_conversation(conversation_id)
    return message

def _get_base_user(user_id: str) -> dict:
    jid_result = supabase.table("xmpp_accounts") \
        .select("jid") \
        .eq("user_id", user_id) \
        .execute()
    if not jid_result.data:
        raise HTTPException(
            status_code=404,
            detail="Cuenta XMPP no encontrada. El registro puede haberse completado sin crear la cuenta XMPP."
        )

    password_result = supabase.rpc("get_xmpp_password", {
        "p_user_id": user_id,
        "p_key": settings.XMPP_ENCRYPTION_KEY
    }).execute()

    return {
        "jid": jid_result.data[0]["jid"],
        "password": password_result.data
    }

def _verify_conversation(conversation_id: str, user_id: str) -> None:
    result = supabase.table("conversations") \
        .select("id") \
        .eq("id", conversation_id) \
        .eq("user_id", user_id) \
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Conversation not found")


async def handle_webhook(payload: BotWebhookPayload) -> None:
    message = _find_message(payload)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    _save_response(message["id"], payload.response)
    if message.get("command_id"):
        _mark_command_executed(message["command_id"])

def _find_message(payload: BotWebhookPayload) -> dict | None:
    body = payload.body
    if "|" in body:
        _, body = body.split("|", 1)
    if payload.message_id:
        result = supabase.table("messages") \
            .select("*") \
            .eq("xmpp_message_id", payload.message_id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
    else:
        result = supabase.table("messages") \
            .select("*") \
            .ilike("body", body) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
    return result.data[0] if result.data else None

def _save_response(message_id: str, response: str) -> None:
    supabase.table("messages").update({"response": response}).eq("id", message_id).execute()

def _mark_command_executed(command_id: str) -> None:
    supabase.table("commands").update({
        "status": "executed",
        "executed_at": "now()"
    }).eq("id", command_id).execute()

def _create_command(user_id: str, device_id: str | None, action: str, payload: dict = {}, status: str = "pending", error: str | None = None) -> str:
    result = supabase.table("commands").insert({
        "user_id":     user_id,
        "device_id":   device_id,
        "action":      action,
        "payload":     payload,
        "status":      status,
        "executed_at": "now()" if status == "executed" else None,
        "error":       error
    }).execute()
    return result.data[0]["id"]


def create_command_from_bot(body: dict) -> dict:
    command_id = _create_command(
        user_id=body["user_id"],
        device_id=body["device_id"],
        action=body["action"],
        payload=body.get("payload", {}),
        status="executed",
        error=body.get("error")
    )

    if body.get("xmpp_message_id"):
        supabase.table("messages").update({
            "command_id": command_id
        }).eq("xmpp_message_id", body["xmpp_message_id"]).execute()

    return {"ok": True, "command_id": command_id}

def _create_message(user_id, command_id, xmpp_message_id, body, conversation_id) -> dict:
    message_data = {
        "from_user_id": user_id,
        "command_id": command_id,
        "xmpp_message_id": xmpp_message_id,
        "body": body,
        "response": None
    }
    if conversation_id:
        message_data["conversation_id"] = conversation_id
    result = supabase.table("messages").insert(message_data).execute()
    return result.data[0]

def _mark_command_sent(command_id: str, xmpp_message_id: str | None) -> None:
    supabase.table("commands").update({
        "xmpp_message_id": xmpp_message_id,
        "status": "sent"
    }).eq("id", command_id).execute()

def get_user_messages(user_id: str) -> list:
    result = supabase.table("messages") \
        .select("*") \
        .eq("from_user_id", user_id) \
        .order("created_at", desc=True) \
        .execute()
    return result.data

def create_conversation(user_id: str, title: str = "Nueva conversación") -> dict:
    result = supabase.table("conversations").insert({
        "user_id": user_id,
        "title": title
    }).execute()
    return result.data[0]

def get_user_conversations(user_id: str) -> list:
    result = supabase.table("conversations") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("updated_at", desc=True) \
        .execute()
    return result.data

def get_conversation_messages(conversation_id: str) -> list:
    result = supabase.table("messages") \
        .select("*") \
        .eq("conversation_id", conversation_id) \
        .order("created_at") \
        .execute()
    return result.data

def _touch_conversation(conversation_id: str) -> None:
    supabase.table("conversations").update({
        "updated_at": "now()"
    }).eq("id", conversation_id).execute()