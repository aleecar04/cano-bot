from typing import Annotated
import hashlib
from fastapi import Header
from app.core.errors import unauthorized
from app.repositories.houses import house_repository


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def bot_auth(authorization: Annotated[str | None, Header()] = None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized("Cabecera Authorization ausente o inválida")
    token = authorization[len("Bearer "):].strip()
    if not token:
        raise unauthorized("Token bearer vacío")
    house = house_repository.find_by_bot_token_hash(_hash(token))
    if not house:
        raise unauthorized("Token de bot inválido")
    return house


BotHouse = Annotated[dict, "House row autenticada por bot_token"]
