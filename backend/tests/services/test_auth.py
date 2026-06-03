from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.services import auth as auth_service


class TestLogin:

    def test_credenciales_validas_devuelve_token(self):
        mock_resp = MagicMock()
        mock_resp.session.access_token = "JWT-XYZ"
        with patch("app.services.auth.supabase") as mock_db:
            mock_db.auth.sign_in_with_password.return_value = mock_resp
            token = auth_service.login("u@e.com", "pass")
        assert token.access_token == "JWT-XYZ"

    def test_credenciales_invalidas_lanza_400(self):
        with patch("app.services.auth.supabase") as mock_db:
            mock_db.auth.sign_in_with_password.side_effect = Exception("bad creds")
            try:
                auth_service.login("u@e.com", "pass")
            except HTTPException as e:
                assert e.status_code == 400
            else:
                raise AssertionError("expected HTTPException")

    def test_sin_session_lanza_400(self):
        mock_resp = MagicMock()
        mock_resp.session = None
        with patch("app.services.auth.supabase") as mock_db:
            mock_db.auth.sign_in_with_password.return_value = mock_resp
            try:
                auth_service.login("u@e.com", "pass")
            except HTTPException as e:
                assert e.status_code == 400
            else:
                raise AssertionError("expected HTTPException")


class TestRequestPasswordRecovery:

    def test_llama_a_supabase(self):
        with patch("app.services.auth.supabase") as mock_db:
            auth_service.request_password_recovery("u@e.com")
        mock_db.auth.reset_password_email.assert_called_once_with("u@e.com")

    def test_silencia_excepcion(self):
        with patch("app.services.auth.supabase") as mock_db:
            mock_db.auth.reset_password_email.side_effect = RuntimeError("boom")
            auth_service.request_password_recovery("u@e.com")  # no lanza


class TestResetPassword:

    def test_token_invalido_lanza_400(self):
        with patch("app.services.auth.verify_password_reset_token", return_value=None):
            try:
                auth_service.reset_password("bad-token", "newpass")
            except HTTPException as e:
                assert e.status_code == 400
            else:
                raise AssertionError("expected HTTPException")

    def test_user_no_existe_lanza_400(self):
        with patch("app.services.auth.verify_password_reset_token", return_value="u@e.com"), \
             patch("app.services.auth.user_repository") as mock_repo:
            mock_repo.find_by_email.return_value = None
            try:
                auth_service.reset_password("tok", "newpass")
            except HTTPException as e:
                assert e.status_code == 400
            else:
                raise AssertionError("expected HTTPException")

    def test_update_falla_lanza_400(self):
        with patch("app.services.auth.verify_password_reset_token", return_value="u@e.com"), \
             patch("app.services.auth.user_repository") as mock_repo, \
             patch("app.services.auth.supabase") as mock_db:
            mock_repo.find_by_email.return_value = {"id": "u1"}
            mock_db.auth.admin.update_user_by_id.side_effect = Exception("boom")
            try:
                auth_service.reset_password("tok", "newpass")
            except HTTPException as e:
                assert e.status_code == 400
            else:
                raise AssertionError("expected HTTPException")

    def test_flujo_completo_ok(self):
        with patch("app.services.auth.verify_password_reset_token", return_value="u@e.com"), \
             patch("app.services.auth.user_repository") as mock_repo, \
             patch("app.services.auth.supabase") as mock_db:
            mock_repo.find_by_email.return_value = {"id": "u1"}
            auth_service.reset_password("tok", "newpass")
        mock_db.auth.admin.update_user_by_id.assert_called_once_with("u1", {"password": "newpass"})
