from unittest.mock import MagicMock, patch
from fastapi import HTTPException
import pytest

from app.services import users as user_service


# ── Read helpers ────────────────────────────────────────────────────────────

class TestResolveJidInHouse:

    def test_jid_desconocido_devuelve_none(self):
        with patch("app.services.users.xmpp_account_repository") as mock_x:
            mock_x.find_user_id_by_jid.return_value = None
            assert user_service.resolve_jid_in_house("foo@x", "h1") is None

    def test_jid_de_otra_casa_devuelve_none(self):
        with patch("app.services.users.xmpp_account_repository") as mock_x, \
             patch("app.services.users.house_member_repository") as mock_h:
            mock_x.find_user_id_by_jid.return_value = "u1"
            mock_h.find_house_id_by_user.return_value = "otra-casa"
            assert user_service.resolve_jid_in_house("u@x", "h1") is None

    def test_jid_propio_devuelve_user_id(self):
        with patch("app.services.users.xmpp_account_repository") as mock_x, \
             patch("app.services.users.house_member_repository") as mock_h:
            mock_x.find_user_id_by_jid.return_value = "u1"
            mock_h.find_house_id_by_user.return_value = "h1"
            assert user_service.resolve_jid_in_house("u@x", "h1") == "u1"


class TestResolveUsernameToEmail:

    def test_username_conocido_devuelve_email(self):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_email_by_username.return_value = "u@e.com"
            assert user_service.resolve_username_to_email("usr") == "u@e.com"

    def test_username_desconocido_lanza_404(self):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_email_by_username.return_value = None
            with pytest.raises(HTTPException) as exc:
                user_service.resolve_username_to_email("ghost")
            assert exc.value.status_code == 404


class TestGetUserById:

    def test_propio_user_devuelto(self):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_by_id.return_value = {"id": "u1"}
            result = user_service.get_user_by_id("u1", {"id": "u1", "is_superuser": False})
        assert result["id"] == "u1"

    def test_user_inexistente_lanza_404(self):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_by_id.return_value = None
            with pytest.raises(HTTPException) as exc:
                user_service.get_user_by_id("ghost", {"id": "u1"})
            assert exc.value.status_code == 404

    def test_otro_user_sin_superuser_403(self):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_by_id.return_value = {"id": "u2"}
            with pytest.raises(HTTPException) as exc:
                user_service.get_user_by_id("u2", {"id": "u1", "is_superuser": False})
            assert exc.value.status_code == 403

    def test_otro_user_con_superuser_devuelto(self):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_by_id.return_value = {"id": "u2"}
            result = user_service.get_user_by_id("u2", {"id": "u1", "is_superuser": True})
        assert result["id"] == "u2"


# ── Create flows ────────────────────────────────────────────────────────────

class TestCreateUserForAdmin:

    def test_email_existente_lanza_400(self):
        from app.models.users import UserCreate
        with patch("app.services.users.get_user_by_email", return_value={"id": "x"}):
            with pytest.raises(HTTPException) as exc:
                user_service.create_user_for_admin(UserCreate(email="u@e.com", password="x123ABC1"))
            assert exc.value.status_code == 400


class TestRegister:

    def test_username_ya_existe_lanza_400(self):
        from app.models.users import UserRegister
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.exists_by_username.return_value = True
            import asyncio
            with pytest.raises(HTTPException) as exc:
                asyncio.run(user_service.register(UserRegister(
                    email="u@e.com", password="X1abcdef", username="usr",
                )))
            assert exc.value.status_code == 400


# ── Profile ─────────────────────────────────────────────────────────────────

class TestGetProfile:

    def test_devuelve_perfil_compuesto(self):
        current_user = {
            "id": "u1", "email": "u@e.com",
            "is_active": True, "is_superuser": False, "created_at": "2025-01-01",
        }
        with patch("app.services.users.user_repository") as mock_u, \
             patch("app.services.users.xmpp_account_repository") as mock_x:
            mock_u.find_basic_by_id.return_value = {
                "username": "u", "first_name": "John", "last_name": "Doe",
            }
            mock_x.find_jid_by_user.return_value = "u@x"
            profile = user_service.get_profile(current_user)
        assert profile["full_name"] == "John Doe"
        assert profile["xmpp_jid"] == "u@x"

    def test_sin_basic_data_full_name_None(self):
        current_user = {"id": "u1", "email": "u@e.com"}
        with patch("app.services.users.user_repository") as mock_u, \
             patch("app.services.users.xmpp_account_repository") as mock_x:
            mock_u.find_basic_by_id.return_value = None
            mock_x.find_jid_by_user.return_value = None
            profile = user_service.get_profile(current_user)
        assert profile["full_name"] is None


# ── Change password ─────────────────────────────────────────────────────────

class TestChangePasswordMe:

    def test_misma_password_lanza_400(self):
        with pytest.raises(HTTPException) as exc:
            user_service.change_password_me("u@e.com", "X1abcdef", "X1abcdef")
        assert exc.value.status_code == 400

    def test_password_actual_invalida_lanza_400(self):
        with patch("app.services.users.supabase") as mock_db:
            mock_db.auth.sign_in_with_password.side_effect = Exception("bad")
            with pytest.raises(HTTPException) as exc:
                user_service.change_password_me("u@e.com", "vieja", "Nueva1ABC")
            assert exc.value.status_code == 400

    def test_password_actualizada_correctamente(self):
        with patch("app.services.users.supabase") as mock_db:
            mock_db.auth.sign_in_with_password.return_value = MagicMock()
            mock_db.auth.admin.update_user_by_id.return_value = MagicMock()
            user_service.change_password_me("u@e.com", "vieja", "Nueva1ABC")
        # No assert error: si no lanza, OK


# ── Admin flows ─────────────────────────────────────────────────────────────

class TestAdminDeleteUser:

    def test_superuser_no_puede_borrarse_a_si_mismo(self):
        current_user = {"id": "u1", "is_superuser": True}
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_by_id.return_value = {"id": "u1"}
            with pytest.raises(HTTPException) as exc:
                user_service.admin_delete_user("u1", current_user)
            assert exc.value.status_code == 403

    def test_user_inexistente_404(self):
        current_user = {"id": "admin"}
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_by_id.return_value = None
            with pytest.raises(HTTPException) as exc:
                user_service.admin_delete_user("ghost", current_user)
            assert exc.value.status_code == 404

    def test_borra_user_de_base_user(self):
        current_user = {"id": "admin"}
        with patch("app.services.users.user_repository") as mock_repo, \
             patch("app.services.users.supabase") as mock_db:
            mock_repo.find_by_id.return_value = {"id": "u1"}
            user_service.admin_delete_user("u1", current_user)
        mock_db.table.assert_called_with("base_user")
