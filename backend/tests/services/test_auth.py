from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.auth import auth_service


class TestAuthService:

    def test_valid_credentials_return_token(self):
        mock_resp = MagicMock()
        mock_resp.session.access_token = "eyJhbGciOiJFUzI1NiJ9.fake"
        with patch("app.services.auth.supabase") as mock_db:
            mock_db.auth.sign_in_with_password.return_value = mock_resp
            assert auth_service.login("anabel@cano-app.com", "CanoBot2026!").access_token == "eyJhbGciOiJFUzI1NiJ9.fake"

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
                auth_service.login("anabel@cano-app.com", "CanoBot2026!")
            assert exc.value.status_code == 400

    def test_request_password_recovery_swallows_exceptions(self):
        with patch("app.services.auth.supabase") as mock_db:
            mock_db.auth.reset_password_email.side_effect = RuntimeError("boom")
            auth_service.request_password_recovery("anabel@cano-app.com")

    @pytest.mark.parametrize("token_email, user, update_error", [
        (None, None, None),
        ("anabel@cano-app.com", None, None),
        ("anabel@cano-app.com", {"id": "user_anabel"}, Exception("boom")),
    ])
    def test_reset_password_failures_raise_400(self, token_email, user, update_error):
        with patch("app.services.auth.verify_password_reset_token", return_value=token_email), \
             patch("app.services.auth.user_repository") as mock_repo, \
             patch("app.services.auth.supabase") as mock_db:
            mock_repo.find_by_email.return_value = user
            if update_error is not None:
                mock_db.auth.admin.update_user_by_id.side_effect = update_error
            with pytest.raises(HTTPException) as exc:
                auth_service.reset_password("tok", "CanoBot2027!")
            assert exc.value.status_code == 400
