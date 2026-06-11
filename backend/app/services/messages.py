import httpx
import inspect
import json
from datetime import date
from typing import Callable

from app.core.db import supabase
from app.core.errors import bad_request, forbidden, not_found, service_unavailable
from app.models.xmpp import BotWebhookPayload
from app.services.xmpp import send_xmpp_message
from app.services.home import get_bot_target_for_user, get_house_id_for_user
from app.services.ollama import classify_intent
from app.services.command_kinds import lookup_prefix_command
from app.repositories.devices import device_repository
from app.repositories.messages import message_repository, conversation_repository
from app.repositories.users import xmpp_account_repository
from app.repositories.houses import house_member_repository
from app.core.config import settings

_NOW = "now()"

# Intents que el backend puede resolver sin pasar por el bot.
_BACKEND_RESOLVED_INTENTS: dict[str, str] = {
    "unknown":      "No te he entendido, prueba de otra forma.",
    "ollama_error": "Estoy teniendo problemas para clasificar tu mensaje, inténtalo de nuevo en breves.",
}

ResolveCallback = Callable[[str, str], object]


class _DeviceNotFound(Exception):
    """Device no encontrado al resolver un control_device."""

class _ValidationError(Exception):
    """Acción no soportada o payload inválido en control_device."""
    def __init__(self, msg: str):
        super().__init__(msg)
        self.message = msg


# ── Entry points públicos ────────────────────────────────────────────────────

async def process_message(body: str, user_id: str, conversation_id: str) -> dict:
    """Mensaje desde la PWA: persiste, clasifica, intenta resolver en backend
    o lo reenvía al bot. La respuesta se guarda en messages.response."""
    _verify_conversation(conversation_id, user_id)
    bot_target = _require_bot_target(user_id)

    message = _create_message(None, body, conversation_id)
    intent_data = await _classify(body)

    if await _try_resolve_in_backend(intent_data, user_id, message, _save_response):
        _touch_conversation(conversation_id)
        return message

    await _forward_to_bot(body, intent_data, message["id"], user_id, bot_target)
    _touch_conversation(conversation_id)
    return message


async def process_gajim_message(from_jid: str, body: str, house_id: str) -> dict:
    user_id = _authenticate_gajim_sender(from_jid, house_id)
    bot_target = _require_bot_target(user_id)
    conv_id = _get_or_create_xmpp_conversation_today(user_id)

    message = _create_message(None, body, conv_id)
    correlation_id = str(message["id"])
    intent_data = await _classify(body)

    async def on_resolve(mid: str, text: str) -> None:
        await _resolve_for_gajim(mid, correlation_id, user_id, text)

    if await _try_resolve_in_backend(intent_data, user_id, message, on_resolve):
        return message

    await _forward_to_bot(body, intent_data, message["id"], user_id, bot_target)
    return message


def handle_webhook(payload: BotWebhookPayload, house_id: str) -> None:
    message = _find_message(payload)
    if message:
        owner = conversation_repository.find_user_id_by_id(message["conversation_id"])
        if not owner or house_member_repository.find_house_id_by_user(owner) != house_id:
            raise forbidden("El mensaje no pertenece a esta casa")
        _save_response(message["id"], payload.response)
        return

    jid_bare = payload.from_jid.split("/")[0]
    user_id = xmpp_account_repository.find_user_id_by_jid(jid_bare)
    if not user_id or house_member_repository.find_house_id_by_user(user_id) != house_id:
        raise not_found("JID desconocido en esta casa")
    conv_id = _get_or_create_xmpp_conversation_today(user_id)
    supabase.table("messages").insert({
        "conversation_id": conv_id,
        "body":            payload.body,
        "response":        payload.response,
    }).execute()


# ── Pasos del pipeline (orquestación) ────────────────────────────────────────

def _require_bot_target(user_id: str) -> str:
    bot_target = get_bot_target_for_user(user_id)
    if not bot_target:
        raise bad_request("La casa no tiene un bot configurado")
    return bot_target


def _authenticate_gajim_sender(from_jid: str, house_id: str) -> str:
    """Resuelve el JID a user_id y valida que pertenezca a la casa autenticada."""
    jid_bare = from_jid.split("/")[0]
    user_id = xmpp_account_repository.find_user_id_by_jid(jid_bare)
    if not user_id or house_member_repository.find_house_id_by_user(user_id) != house_id:
        raise not_found("JID desconocido en esta casa")
    return user_id


async def _classify(body: str) -> dict | None:
    intent_data = lookup_prefix_command(body)
    if intent_data is not None:
        return intent_data
    if body.startswith("!"):
        return None  # !comando desconocido — backend lo resuelve sin clasificar
    return await classify_intent(body)


async def _try_resolve_in_backend(
    intent_data: dict | None, user_id: str, message: dict,
    on_resolve: ResolveCallback,
) -> bool:
    message_id = message["id"]

    if intent_data is None:
        # !comando desconocido detectado en _classify
        await _maybe_await(on_resolve(message_id, _BACKEND_RESOLVED_INTENTS["unknown"]))
        return True

    intent = intent_data.get("intent")

    if intent == "control_device":
        try:
            await _dispatch_device_from_nlp(intent_data, user_id, message_id)
            return True
        except _ValidationError as e:
            await _maybe_await(on_resolve(message_id, e.message))
            return True
        except _DeviceNotFound:
            await _maybe_await(on_resolve(message_id, _device_not_found_message(intent_data)))
            return True

    if intent in _BACKEND_RESOLVED_INTENTS:
        await _maybe_await(on_resolve(message_id, _BACKEND_RESOLVED_INTENTS[intent]))
        return True

    return False


async def _maybe_await(result: object) -> None:
    if inspect.isawaitable(result):
        await result


def _device_not_found_message(intent_data: dict) -> str:
    name = intent_data.get("device") or ""
    if name:
        return f"No he encontrado ningún dispositivo llamado '{name}'."
    return "No he entendido qué dispositivo quieres controlar."


async def _forward_to_bot(
    body: str, intent_data: dict | None, message_id: str, user_id: str, bot_target: str,
) -> None:
    correlation_id = message_id
    payload = json.dumps({
        "type": "natural_classified",
        "intent_data": intent_data,
        "original_body": body,
    })
    xmpp_body = f"{correlation_id}|{payload}"
    xmpp_account = _get_base_user(user_id)
    try:
        await send_xmpp_message(
            xmpp_body, xmpp_account["jid"], xmpp_account["password"],
            to_jid=bot_target, message_id=correlation_id,
        )
    except httpx.HTTPStatusError as e:
        supabase.table("messages").delete().eq("id", message_id).execute()
        raise service_unavailable(
            f"Error enviando mensaje XMPP: {e.response.status_code} {e.response.text[:200]}"
        )
    except Exception as e:
        supabase.table("messages").delete().eq("id", message_id).execute()
        raise service_unavailable(f"Servicio XMPP no disponible: {e}")


async def _dispatch_device_from_nlp(intent_data: dict, user_id: str, message_id: str) -> None:
    from app.services.command_executor import execute_command, CommandSource
    from app.services.device_catalog import is_action_supported, validate_payload

    action = intent_data.get("action")
    name = (intent_data.get("device") or "").lower()
    if not action or not name:
        raise _DeviceNotFound

    house_id = get_house_id_for_user(user_id)
    if not house_id:
        raise _DeviceNotFound

    device = device_repository.find_by_name_and_house(name, house_id)
    if not device:
        raise _DeviceNotFound

    if not is_action_supported(device.get("type", ""), action):
        raise _ValidationError(f"{device['name']} no soporta la acción '{action}'.")

    payload = intent_data.get("payload") or {}
    err = validate_payload(action, payload)
    if err:
        raise _ValidationError(err)

    result = await execute_command(
        action=action, payload=payload, user_id=user_id,
        source=CommandSource(source_type="conversation", source_id=message_id),
        device_id=device["id"],
    )
    command_id = result.get("command_id")
    if command_id:
        supabase.table("messages").update({"command_id": command_id}).eq("id", message_id).execute()


async def _resolve_for_gajim(message_id: str, correlation_id: str, user_id: str, text: str) -> None:
    _save_response(message_id, text)
    bot_target = get_bot_target_for_user(user_id)
    if not bot_target:
        return
    payload = json.dumps({"type": "relay", "text": text})
    xmpp_account = _get_base_user(user_id)
    try:
        await send_xmpp_message(
            f"{correlation_id}|{payload}",
            xmpp_account["jid"], xmpp_account["password"],
            to_jid=bot_target, message_id=correlation_id,
        )
    except Exception:
        pass


# ── Helpers de acceso a datos ────────────────────────────────────────────────

def _get_base_user(user_id: str) -> dict:
    jid_result = supabase.table("xmpp_accounts") \
        .select("jid") \
        .eq("user_id", user_id) \
        .execute()
    if not jid_result.data:
        raise not_found(
            "Cuenta XMPP no encontrada. El registro puede haberse completado sin crear la cuenta XMPP."
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
    if not conversation_repository.find_by_id_and_user(conversation_id, user_id):
        raise not_found("Conversación no encontrada")


def _get_or_create_xmpp_conversation_today(user_id: str) -> str:
    title = f"XMPP - {date.today().isoformat()}"
    existing = conversation_repository.find_by_user_and_title(user_id, title)
    if existing:
        return existing["id"]
    new_conv = supabase.table("conversations").insert(
        {"user_id": user_id, "title": title}
    ).execute()
    return new_conv.data[0]["id"]


def _find_message(payload: BotWebhookPayload) -> dict | None:
    if not payload.message_id:
        return None
    return message_repository.find_by_id(payload.message_id)


def _save_response(message_id: str, response: str) -> None:
    supabase.table("messages").update({"response": response}).eq("id", message_id).execute()


def _touch_conversation(conversation_id: str) -> None:
    supabase.table("conversations").update({
        "updated_at": _NOW
    }).eq("id", conversation_id).execute()


def _create_message(command_id, body, conversation_id) -> dict:
    result = supabase.table("messages").insert({
        "conversation_id": conversation_id,
        "command_id":      command_id,
        "body":            body,
        "response":        None,
    }).execute()
    return result.data[0]


# ── CRUD simple ──────────────────────────────────────────────────────────────

def get_user_messages(user_id: str) -> list:
    conv_ids = conversation_repository.find_ids_by_user(user_id)
    return message_repository.find_by_conversation_ids(conv_ids)


def create_conversation(user_id: str, title: str = "Nueva conversación") -> dict:
    result = supabase.table("conversations").insert({
        "user_id": user_id,
        "title": title
    }).execute()
    return result.data[0]


def get_user_conversations(user_id: str) -> list:
    return conversation_repository.find_by_user(user_id)


def get_conversation_messages(conversation_id: str) -> list:
    return message_repository.find_by_conversation(conversation_id)
