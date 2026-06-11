import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.users import UserRegister
from app.services import users as user_service


_VALID = {"email": "anabel@cano-app.com", "username": "anabel", "password": "CanoBot2026!"}


class TestUsersService:

    @pytest.mark.parametrize("first, last, expected_first, expected_last", [
        ("  ana  ",    "lopez",    "Ana",   "Lopez"),
        ("MARINA",     "GARCIA",   "Marina", "Garcia"),
        (None,         None,        None,    None),
    ])
    def test_name_normalize(self, first, last, expected_first, expected_last):
        u = UserRegister(**_VALID, first_name=first, last_name=last)
        assert u.first_name == expected_first and u.last_name == expected_last

    @pytest.mark.parametrize("bad_username", ["AB", "with-dash"])
    def test_validate_username(self, bad_username):
        with pytest.raises(ValidationError):
            UserRegister(**{**_VALID, "username": bad_username})

    def test_validate_name(self):
        with pytest.raises(ValidationError):
            UserRegister(**_VALID, first_name="Ana2")

    @pytest.mark.parametrize("user_id, house_id, expected", [
        (None,           None,         None),
        ("user_anabel",  "otra_casa",  None),
        ("user_anabel",  "casa_demo",  "user_anabel"),
    ])
    def test_resolve_jid(self, user_id, house_id, expected):
        with patch("app.services.users.xmpp_account_repository") as mock_x, \
             patch("app.services.users.house_member_repository") as mock_h:
            mock_x.find_user_id_by_jid.return_value = user_id
            mock_h.find_house_id_by_user.return_value = house_id
            assert user_service.resolve_jid_in_house("anabel@xmpp.cano-app.com", "casa_demo") == expected

    def test_resolve_username(self):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_email_by_username.return_value = "anabel@cano-app.com"
            assert user_service.resolve_username_to_email("anabel") == "anabel@cano-app.com"

            mock_repo.find_email_by_username.return_value = None
            with pytest.raises(HTTPException) as exc:
                user_service.resolve_username_to_email("fantasma")
            assert exc.value.status_code == 404

    def test_register_with_taken_username_raises_400(self):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.exists_by_username.return_value = True
            with pytest.raises(HTTPException) as exc:
                asyncio.run(user_service.register(UserRegister(
                    email="anabel@cano-app.com", password="CanoBot2026!", username="anabel",
                )))
            assert exc.value.status_code == 400

    def test_get_profile(self):
        current_user = {
            "id": "user_anabel", "email": "anabel@cano-app.com",
            "is_active": True, "created_at": "2025-01-01",
        }
        with patch("app.services.users.user_repository") as mock_u, \
             patch("app.services.users.xmpp_account_repository") as mock_x:
            mock_u.find_basic_by_id.return_value = {"username": "anabel", "first_name": "Ana", "last_name": "Lopez"}
            mock_x.find_jid_by_user.return_value = "anabel@xmpp.cano-app.com"
            profile = user_service.get_profile(current_user)
        assert profile["full_name"] == "Ana Lopez" and profile["xmpp_jid"] == "anabel@xmpp.cano-app.com"

    def test_regenerate_xmpp_password_without_account_raises_404(self):
        with patch("app.services.users.xmpp_account_repository") as mock_x:
            mock_x.find_jid_by_user.return_value = None
            with pytest.raises(HTTPException) as exc:
                asyncio.run(user_service.regenerate_xmpp_password("user_anabel"))
            assert exc.value.status_code == 404

    def test_regenerate_xmpp_password_returns_jid_and_new_password(self):
        with patch("app.services.users.xmpp_account_repository") as mock_x, \
             patch("app.services.users.change_xmpp_password", new_callable=MagicMock) as mock_chg, \
             patch("app.services.users.supabase"):
            mock_x.find_jid_by_user.return_value = "anabel@xmpp.cano-app.com"
            mock_chg.return_value = asyncio.sleep(0)
            result = asyncio.run(user_service.regenerate_xmpp_password("user_anabel"))
        assert result["xmpp_jid"] == "anabel@xmpp.cano-app.com"
        assert len(result["xmpp_password"]) > 10
