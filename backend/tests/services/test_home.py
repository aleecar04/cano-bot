from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import home as home_service


# ── token helpers ────────────────────────────────────────────────────────────

# ── generate_invitation_code ─────────────────────────────────────────────────

def test_generate_invitation_code_format():
    with patch("app.services.home.house_invitation_repository"), \
         patch("app.services.home.supabase"):
        code = home_service.generate_invitation_code("h1", "u1")
    assert len(code) == 6 and all(c.isalnum() and c.upper() == c for c in code)


# ── consume_invitation_code ──────────────────────────────────────────────────

class TestConsumeInvitationCode:

    @pytest.mark.parametrize("stored", [
        None,
        {"house_id": "h1", "expires_at": "1970-01-01T00:00:00+00:00"},
    ])
    def test_unknown_or_expired_code_raises_400(self, stored):
        with patch("app.services.home.house_invitation_repository") as mock_inv:
            mock_inv.find_unused_by_code.return_value = stored
            with pytest.raises(HTTPException) as exc:
                home_service.consume_invitation_code("X", "u1")
            assert exc.value.status_code == 400

    def test_valid_code_inserts_member_and_returns_house(self):
        from datetime import datetime, timedelta, timezone
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        with patch("app.services.home.house_invitation_repository") as mock_inv, \
             patch("app.services.home.house_repository") as mock_h, \
             patch("app.services.home.supabase"):
            mock_inv.find_unused_by_code.return_value = {
                "id": "i1", "code": "GOOD", "house_id": "h1", "expires_at": future,
            }
            mock_h.find_by_id.return_value = {"id": "h1", "name": "Casa"}
            assert home_service.consume_invitation_code("GOOD", "u1")["id"] == "h1"


# ── Helpers ──────────────────────────────────────────────────────────────────

class TestGetUserHouse:

    @pytest.mark.parametrize("house_id, expected", [
        (None, None),
        ("h1", {"id": "h1"}),
    ])
    def test_returns_house_or_none(self, house_id, expected):
        with patch("app.services.home.house_member_repository") as mock_hm, \
             patch("app.services.home.house_repository") as mock_h:
            mock_hm.find_house_id_by_user.return_value = house_id
            mock_h.find_by_id.return_value = expected
            assert home_service.get_user_house("u1") == expected


class TestGetBotTargetForUser:

    @pytest.mark.parametrize("house_id, house, expected", [
        (None, None, None),
        ("h1", {"id": "h1"}, None),                                      # no bot_token_hash
    ])
    def test_returns_none_when_missing_house_or_token(self, house_id, house, expected):
        with patch("app.services.home.house_member_repository") as mock_hm, \
             patch("app.services.home.house_repository") as mock_h:
            mock_hm.find_house_id_by_user.return_value = house_id
            mock_h.find_by_id.return_value = house
            assert home_service.get_bot_target_for_user("u1") is expected

    def test_returns_jid_with_resource_when_token_present(self):
        with patch("app.services.home.house_member_repository") as mock_hm, \
             patch("app.services.home.house_repository") as mock_h, \
             patch("app.core.config.settings") as mock_s:
            mock_hm.find_house_id_by_user.return_value = "h1"
            mock_h.find_by_id.return_value = {"id": "h1", "bot_token_hash": "abcdef1234567890"}
            mock_s.XMPP_BOT_JID = "bot@xmpp"
            result = home_service.get_bot_target_for_user("u1")
        assert "bot@xmpp" in result and "bot-abcdef123456" in result


class TestRequireHouseAndOwner:

    def test_require_owner_raises_403_for_non_owner(self):
        with patch("app.services.home.get_user_role", return_value="member"):
            with pytest.raises(HTTPException) as exc:
                home_service.require_owner("u1")
            assert exc.value.status_code == 403

class TestGetHouseMemberIds:

    def test_returns_full_member_list_when_house_exists(self):
        with patch("app.services.home.house_member_repository") as mock_h:
            mock_h.find_house_id_by_user.return_value = "h1"
            mock_h.find_user_ids_by_house.return_value = ["u1", "u2"]
            assert home_service.get_house_member_ids("u1") == ["u1", "u2"]


# ── setup_house ──────────────────────────────────────────────────────────────

class TestSetupHouse:

    def test_user_already_in_house_raises_409(self):
        with patch("app.services.home.get_house_id_for_user", return_value="h_existente"), \
             pytest.raises(HTTPException) as exc:
            home_service.setup_house("u1", "Mi Casa")
        assert exc.value.status_code == 409

    def test_full_flow_returns_house_id_and_token(self):
        with patch("app.services.home.get_house_id_for_user", return_value=None), \
             patch("app.services.home.supabase") as mock_db:
            houses_chain = MagicMock()
            houses_chain.execute.return_value.data = [{"id": "h_new"}]

            def table_side(name):
                m = MagicMock()
                if name == "houses":
                    m.insert.return_value = houses_chain
                else:
                    m.insert.return_value.execute.return_value = MagicMock()
                m.delete.return_value.eq.return_value.execute.return_value = MagicMock()
                return m
            mock_db.table.side_effect = table_side

            result = home_service.setup_house("u1", "X")
        assert result["house_id"] == "h_new" and isinstance(result["bot_token"], str)

    def test_rolls_back_house_when_member_insert_fails(self):
        with patch("app.services.home.get_house_id_for_user", return_value=None), \
             patch("app.services.home.supabase") as mock_db:
            houses_chain = MagicMock()
            houses_chain.execute.return_value.data = [{"id": "h_new"}]

            def table_side(name):
                m = MagicMock()
                if name == "houses":
                    m.insert.return_value = houses_chain
                    m.delete.return_value.eq.return_value.execute.return_value = MagicMock()
                else:
                    m.insert.return_value.execute.side_effect = RuntimeError("members fail")
                return m
            mock_db.table.side_effect = table_side
            with pytest.raises(RuntimeError):
                home_service.setup_house("u1", "X")
            calls = [c.args[0] for c in mock_db.table.call_args_list]
            assert calls.count("houses") >= 2


def test_regenerate_bot_token_returns_new_token():
    with patch("app.services.home.require_owner"), \
         patch("app.services.home.require_house", return_value="h1"), \
         patch("app.services.home.supabase"):
        token = home_service.regenerate_bot_token("u1")
    assert isinstance(token, str) and len(token) > 20
