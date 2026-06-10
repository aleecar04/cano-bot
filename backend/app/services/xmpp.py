import uuid

import httpx
import secrets
from app.core.config import settings

def _admin_auth() -> tuple:
    return (settings.XMPP_ADMIN_USER, settings.XMPP_ADMIN_PASSWORD)

def _base_headers() -> dict:
    return {"Content-Type": "application/json"}


async def create_xmpp_account(username: str) -> str:
    xmpp_password = secrets.token_urlsafe(16)
    jid = f"{username}@{settings.XMPP_DOMAIN}"

    async with httpx.AsyncClient(verify=True, timeout=10.0) as client:
        session_id = await _start_add_user_command(client)
        await _complete_add_user_command(client, session_id, jid, xmpp_password)

    return xmpp_password


async def _start_add_user_command(client: httpx.AsyncClient) -> str:
    r = await client.post(
        settings.XMPP_REST_URL,
        auth=_admin_auth(),
        headers=_base_headers(),
        json={
            "kind": "iq",
            "type": "set",
            "to": settings.XMPP_DOMAIN,
            "command": {
                "node": "http://jabber.org/protocol/admin#add-user",
                "action": "execute"
            }
        }
    )
    r.raise_for_status()
    return r.json()["command"]["sessionid"]


async def _complete_add_user_command(client: httpx.AsyncClient, session_id: str, jid: str, password: str) -> None:
    r = await client.post(
        settings.XMPP_REST_URL,
        auth=_admin_auth(),
        headers=_base_headers(),
        json={
            "kind": "iq",
            "type": "set",
            "to": settings.XMPP_DOMAIN,
            "command": {
                "node": "http://jabber.org/protocol/admin#add-user",
                "action": "complete",
                "sessionid": session_id,
                "data": {
                    "accountjid": jid,
                    "password": password,
                    "password-verify": password
                }
            }
        }
    )
    r.raise_for_status()


async def is_bot_online(bot_jid: str, timeout: float = 3.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                settings.XMPP_REST_URL,
                auth=_admin_auth(),
                headers=_base_headers(),
                json={"kind": "iq", "type": "get", "to": bot_jid, "ping": {}},
            )
        return r.status_code == 200 and r.json().get("type") == "result"
    except Exception:
        return False


async def send_xmpp_message(
    body: str, from_jid: str, xmpp_password: str, to_jid: str, message_id: str | None = None
) -> str | None:
    username = from_jid.split("@")[0]
    message_id = message_id or str(uuid.uuid4())
    recipient = to_jid
    async with httpx.AsyncClient(verify=True, timeout=10.0) as client:
        r = await client.post(
            settings.XMPP_REST_URL,
            auth=(username, xmpp_password),
            headers=_base_headers(),
            json={
                "kind": "message",
                "type": "chat",
                "id": message_id,
                "to": recipient,
                "body": body
            }
        )
        r.raise_for_status()
        return message_id