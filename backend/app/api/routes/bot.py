from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header

from app.api.bot_auth import bot_auth
from app.core.config import settings
from app.core.errors import unauthorized
from app.services.bot_auth import bot_auth_service

router = APIRouter(prefix="/bot", tags=["bot"])
internal_router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/xmpp-token")
def issue_xmpp_token(house: Annotated[dict, Depends(bot_auth)]) -> dict:
    """Emite un token efimero de un solo uso para que la instancia del bot
    se autentique contra Prosody via SASL OAUTHBEARER."""
    return bot_auth_service.issue_token(house["id"])


@internal_router.post("/introspect")
def introspect_token(
    payload: Annotated[dict, Body()],
    x_prosody_secret: Annotated[str | None, Header()] = None,
) -> dict:
    if x_prosody_secret != settings.PROSODY_INTROSPECT_SECRET:
        raise unauthorized("Secreto de introspección inválido")

    token = (payload.get("token") or "").strip()
    meta = bot_auth_service.consume_token(token)
    if not meta:
        return {"active": False}

    return {
        "active": True,
        "username": settings.XMPP_BOT_JID,
        "scope": "xmpp",
        "exp": int(meta["exp"]),
    }
