import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import users as user_service


# ── resolve_jid_in_house ─────────────────────────────────────────────────────

class TestResolveJidInHouse:

    @pytest.mark.parametrize("user_id, house_id, expected", [
        (None, None, None),
        ("u1", "otra-casa", None),
        ("u1", "h1", "u1"),
    ])
    def test_returns_user_id_only_when_jid_belongs_to_same_house(self, user_id, house_id, expected):
        with patch("app.services.users.xmpp_account_repository") as mock_x, \
             patch("app.services.users.house_member_repository") as mock_h:
            mock_x.find_user_id_by_jid.return_value = user_id
            mock_h.find_house_id_by_user.return_value = house_id
            assert user_service.resolve_jid_in_house("u@x", "h1") == expected


def test_resolve_username_to_email_returns_email_or_raises_404():
    with patch("app.services.users.user_repository") as mock_repo:
        mock_repo.find_email_by_username.return_value = "u@e.com"
        assert user_service.resolve_username_to_email("usr") == "u@e.com"

    with patch("app.services.users.user_repository") as mock_repo:
        mock_repo.find_email_by_username.return_value = None
        with pytest.raises(HTTPException) as exc:
            user_service.resolve_username_to_email("ghost")
        assert exc.value.status_code == 404


# ── get_user_by_id ───────────────────────────────────────────────────────────

class TestGetUserById:

    @pytest.mark.parametrize("is_superuser, expected_status_or_id", [
        (False, 403),
        (True, "u2"),
    ])
    def test_other_user_only_accessible_to_superuser(self, is_superuser, expected_status_or_id):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_by_id.return_value = {"id": "u2"}
            if isinstance(expected_status_or_id, int):
                with pytest.raises(HTTPException) as exc:
                    user_service.get_user_by_id("u2", {"id": "u1", "is_superuser": is_superuser})
                assert exc.value.status_code == expected_status_or_id
            else:
                result = user_service.get_user_by_id("u2", {"id": "u1", "is_superuser": is_superuser})
                assert result["id"] == expected_status_or_id


# ── Create flows ─────────────────────────────────────────────────────────────

def test_create_user_for_admin_with_existing_email_raises_400():
    from app.models.users import UserCreate
    with patch("app.services.users.get_user_by_email", return_value={"id": "x"}), \
         pytest.raises(HTTPException) as exc:
        user_service.create_user_for_admin(UserCreate(email="u@e.com", password="x123ABC1"))
    assert exc.value.status_code == 400


@pytest.mark.parametrize("first, last, expected_first, expected_last", [
    ("  ana    garcía  ", "PÉREZ", "Ana García", "Pérez"),
    ("maría josé", "o'connor", "María José", "O'Connor"),
])
def test_register_normalizes_first_and_last_name(first, last, expected_first, expected_last):
    from app.models.users import UserRegister
    u = UserRegister(email="u@e.com", password="X1abcdef", username="usr",
                     first_name=first, last_name=last)
    assert u.first_name == expected_first and u.last_name == expected_last


def test_register_rejects_invalid_chars_in_name():
    from app.models.users import UserRegister
    with pytest.raises(ValueError):
        UserRegister(email="u@e.com", password="X1abcdef", username="usr",
                     first_name="Ana123", last_name="Pérez")


def test_register_with_existing_username_raises_400():
    from app.models.users import UserRegister
    with patch("app.services.users.user_repository") as mock_repo:
        mock_repo.exists_by_username.return_value = True
        with pytest.raises(HTTPException) as exc:
            asyncio.run(user_service.register(UserRegister(
                email="u@e.com", password="X1abcdef", username="usr",
            )))
        assert exc.value.status_code == 400


# ── Profile ──────────────────────────────────────────────────────────────────

class TestGetProfile:

    def test_returns_composed_profile_with_full_name_and_jid(self):
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
        assert profile["full_name"] == "John Doe" and profile["xmpp_jid"] == "u@x"

# ── change_password_me ───────────────────────────────────────────────────────

class TestChangePasswordMe:

    def test_same_password_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            user_service.change_password_me("u@e.com", "X1abcdef", "X1abcdef")
        assert exc.value.status_code == 400

    def test_invalid_current_password_raises_400(self):
        with patch("app.services.users.supabase") as mock_db:
            mock_db.auth.sign_in_with_password.side_effect = Exception("bad")
            with pytest.raises(HTTPException) as exc:
                user_service.change_password_me("u@e.com", "vieja", "Nueva1ABC")
            assert exc.value.status_code == 400

    def test_valid_password_change_succeeds(self):
        with patch("app.services.users.supabase") as mock_db:
            mock_db.auth.sign_in_with_password.return_value = MagicMock()
            mock_db.auth.admin.update_user_by_id.return_value = MagicMock()
            user_service.change_password_me("u@e.com", "vieja", "Nueva1ABC")


# ── admin_delete_user ────────────────────────────────────────────────────────

class TestUpdateMeAndAdminUpdate:

    def test_update_me_with_conflicting_email_raises_409(self):
        from app.models.users import UserUpdateMe
        with patch("app.services.users.get_user_by_email",
                   return_value={"id": "other-user", "email": "x@e.com"}), \
             pytest.raises(HTTPException) as exc:
            user_service.update_me("u1", UserUpdateMe(email="x@e.com"))
        assert exc.value.status_code == 409

    def test_admin_update_user_raises_404_when_missing(self):
        from app.models.users import UserUpdate
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_by_id.return_value = None
            with pytest.raises(HTTPException) as exc:
                user_service.admin_update_user("ghost", UserUpdate(email="x@e.com"))
            assert exc.value.status_code == 404


def test_delete_me_rejects_superuser():
    with pytest.raises(HTTPException) as exc:
        user_service.delete_me({"id": "u1", "is_superuser": True})
    assert exc.value.status_code == 403


class TestAdminDeleteUser:

    def test_superuser_cannot_delete_themselves(self):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_by_id.return_value = {"id": "u1"}
            with pytest.raises(HTTPException) as exc:
                user_service.admin_delete_user("u1", {"id": "u1", "is_superuser": True})
            assert exc.value.status_code == 403

    def test_missing_user_raises_404(self):
        with patch("app.services.users.user_repository") as mock_repo:
            mock_repo.find_by_id.return_value = None
            with pytest.raises(HTTPException) as exc:
                user_service.admin_delete_user("ghost", {"id": "admin"})
            assert exc.value.status_code == 404

    def test_deletes_user_from_base_user_table(self):
        with patch("app.services.users.user_repository") as mock_repo, \
             patch("app.services.users.supabase") as mock_db:
            mock_repo.find_by_id.return_value = {"id": "u1"}
            user_service.admin_delete_user("u1", {"id": "admin"})
        mock_db.table.assert_called_with("base_user")
