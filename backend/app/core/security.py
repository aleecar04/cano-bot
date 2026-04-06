from datetime import datetime, timedelta, timezone

import jwt
from app.core.config import settings

ALGORITHM = "HS256"

def create_password_reset_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    return jwt.encode({"sub": email, "exp": expire}, settings.SECRET_KEY, algorithm=ALGORITHM)

def verify_password_reset_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None