from fastapi import HTTPException
from app.core.db import supabase
from app.models import BotWebhookPayload
from app.services.xmpp import send_xmpp_message
from app.services.home import get_bot_jid_for_user
from app.core.config import settings

_NOW = "now()"

async def process_message(body: str, user_id: str, conversation_id: str | None) -> dict:
    import httpx as _httpx
    xmpp_account = _get_base_user(user_id)
    if conversation_id:
        _verify_conversation(conversation_id, user_id)

    bot_jid = get_bot_jid_for_user(user_id)
    if not bot_jid:
        raise HTTPException(status_code=400, detail="La casa no tiene un bot configurado")

    try:
        xmpp_message_id = await send_xmpp_message(
            body,
            xmpp_account["jid"],
            xmpp_account["password"],
            to_jid=bot_jid,
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


def handle_webhook(payload: BotWebhookPayload) -> None:
    message = _find_message(payload)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    _save_response(message["id"], payload.response)

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


def update_command_result(command_id: str, error: str | None) -> None:
    error = error or None  # normalize empty string to None
    status = "failed" if error else "executed"
    data: dict = {"status": status, "executed_at": _NOW}
    if error:
        data["error"] = error
    supabase.table("commands").update(data).eq("id", command_id).execute()

def _create_command(
    user_id: str,
    device_id: str | None,
    action: str,
    payload: dict = {},
    status: str = "pending",
    error: str | None = None,
    source_type: str = "conversation",
    source_id: str | None = None,
) -> str:
    result = supabase.table("commands").insert({
        "user_id":     user_id,
        "device_id":   device_id,
        "action":      action,
        "payload":     payload,
        "status":      status,
        "executed_at": _NOW if status == "executed" else None,
        "error":       error,
        "source_type": source_type,
        "source_id":   source_id,
    }).execute()
    return result.data[0]["id"]


def create_command_from_bot(body: dict) -> dict:
    # Scheduler passes pending=True to register the command before executing
    if body.get("pending"):
        status, error = "pending", None
    else:
        error = body.get("error") or None
        status = "failed" if error else "executed"

    command_id = _create_command(
        user_id=body["user_id"],
        device_id=body["device_id"],
        action=body["action"],
        payload=body.get("payload", {}),
        status=status,
        error=error,
        source_type=body.get("source_type") or "conversation",
        source_id=body.get("source_id") or None,
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
        "updated_at": _NOW
    }).eq("id", conversation_id).execute()