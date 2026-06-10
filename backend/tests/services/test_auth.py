from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import auth as auth_service


class TestLogin:

    def test_valid_credentials_return_token(self):
        mock_resp = MagicMock(); mock_resp.session.access_token = "JWT-XYZ"
        with patch("app.services.auth.supabase") as mock_db:
            mock_db.auth.sign_in_with_password.return_value = mock_resp
            assert auth_service.login("u@e.com", "pass").access_token == "JWT-XYZ"

    @pytest.mark.parametrize("setup", [
        lambda mock_db: setattr(mock_db.auth, "sign_in_with_password",
                                MagicMock(side_effect=Exception("bad creds"))),
        lambda mock_db: setattr(mock_db.auth, "sign_in_with_password",
                                MagicMock(return_value=MagicMock(session=None))),
    ])
    def test_invalid_response_raises_400(self, setup):
        with patch("app.services.auth.supabase") as mock_db:
            setup(mock_db)
            with pytest.raises(HTTPException) as exc:
                auth_service.login("u@e.com", "pass")
            assert exc.value.status_code == 400


class TestRequestPasswordRecovery:

    def test_swallows_supabase_exception(self):
        with patch("app.services.auth.supabase") as mock_db:
            mock_db.auth.reset_password_email.side_effect = RuntimeError("boom")
            auth_service.request_password_recovery("u@e.com")


class TestResetPassword:

    @pytest.mark.parametrize("token_email, user, update_error", [
        (None, None, None),                                  # invalid token
        ("u@e.com", None, None),                             # user not found
        ("u@e.com", {"id": "u1"}, Exception("boom")),        # supabase update fails
    ])
    def test_failures_raise_400(self, token_email, user, update_error):
        with patch("app.services.auth.verify_password_reset_token", return_value=token_email), \
             patch("app.services.auth.user_repository") as mock_repo, \
             patch("app.services.auth.supabase") as mock_db:
            mock_repo.find_by_email.return_value = user
            if update_error is not None:
                mock_db.auth.admin.update_user_by_id.side_effect = update_error
            with pytest.raises(HTTPException) as exc:
                auth_service.reset_password("tok", "newpass")
            assert exc.value.status_code == 400

