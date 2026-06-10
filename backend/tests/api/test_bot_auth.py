import hashlib
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.bot_auth import bot_auth


@pytest.mark.parametrize("header", [None, "Token abc", "Bearer "])
def test_bot_auth_rejects_invalid_header(header):
    with pytest.raises(HTTPException) as exc:
        bot_auth(authorization=header)
    assert exc.value.status_code == 401


def test_bot_auth_returns_house_when_token_matches():
    token = "secret-token"
    house = {"id": "h1", "name": "Casa"}
    with patch("app.api.bot_auth.house_repository.find_by_bot_token_hash",
               return_value=house) as mock_find:
        result = bot_auth(authorization=f"Bearer {token}")
    assert result == house
    mock_find.assert_called_once_with(hashlib.sha256(token.encode()).hexdigest())


def test_bot_auth_rejects_unknown_token():
    with patch("app.api.bot_auth.house_repository.find_by_bot_token_hash", return_value=None):
        with pytest.raises(HTTPException) as exc:
            bot_auth(authorization="Bearer fake-token")
    assert exc.value.status_code == 401
