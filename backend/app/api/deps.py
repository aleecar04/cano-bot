from typing import Annotated
import json
import httpx
import jwt
from jwt.algorithms import ECAlgorithm
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from app.core.config import settings
from app.core.db import supabase
from app.models import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

TokenDep = Annotated[str, Depends(reusable_oauth2)]

_cached_public_key = None

def get_supabase_public_key():
    global _cached_public_key
    if _cached_public_key is not None:
        return _cached_public_key
    response = httpx.get(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json", timeout=5.0)
    response.raise_for_status()
    jwks = response.json()
    key_data = jwks["keys"][0]
    _cached_public_key = ECAlgorithm.from_jwk(json.dumps(key_data))
    return _cached_public_key


def get_current_user(token: TokenDep) -> dict:
    try:
        public_key = get_supabase_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["ES256"],
            options={"verify_aud": False}
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError) as e:
        print(f"ERROR JWT: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    result = supabase.table("base_user").select("*").eq("id", token_data.sub).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = result.data[0]
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User is not active")
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> dict:
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user