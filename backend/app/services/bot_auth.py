from __future__ import annotations

import secrets
import time

from app.core.config import settings

_TOKENS: dict[str, dict] = {}


def _purge_expired() -> None:
    now = time.time()
    expired = [t for t, meta in _TOKENS.items() if meta["exp"] < now]
    for t in expired:
        _TOKENS.pop(t, None)


class BotAuthService:

    def issue_token(self, house_id: str) -> dict:
        _purge_expired()
        token = secrets.token_urlsafe(32)
        _TOKENS[token] = {
            "status": "pending",
            "exp": time.time() + settings.BOT_XMPP_TOKEN_TTL_S,
            "house_id": house_id,
        }
        return {
            "username": settings.XMPP_BOT_JID,
            "password": token,
            "expires_in": settings.BOT_XMPP_TOKEN_TTL_S,
        }

    def consume_token(self, token: str) -> dict | None:
        _purge_expired()
        meta = _TOKENS.get(token)
        if not meta or meta["status"] != "pending":
            return None
        meta["status"] = "consumed"
        return meta


bot_auth_service = BotAuthService()
