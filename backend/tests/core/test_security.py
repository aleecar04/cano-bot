import jwt

from app.core.config import settings
from app.core.security import verify_password_reset_token


def test_verify_password_reset_token_returns_subject_or_none():
    token = jwt.encode({"sub": "user@example.com"}, settings.SECRET_KEY, algorithm="HS256")
    assert verify_password_reset_token(token) == "user@example.com"
    assert verify_password_reset_token("not-a-valid-token") is None
