from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import home as home_service


class TestHomeService:

    def test_generate_invitation_code_format(self):
        with patch("app.services.home.house_invitation_repository"), \
             patch("app.services.home.supabase"):
            code = home_service.generate_invitation_code("casa_demo", "user_anabel")
        assert len(code) == 6 and all(c.isalnum() and c.upper() == c for c in code)

    @pytest.mark.parametrize("stored", [
        None,
        {"house_id": "casa_demo", "expires_at": "1970-01-01T00:00:00+00:00"},
    ])
    def test_unknown_or_expired_code_raises_400(self, stored):
        with patch("app.services.home.house_invitation_repository") as mock_inv:
            mock_inv.find_unused_by_code.return_value = stored
            with pytest.raises(HTTPException) as exc:
                home_service.consume_invitation_code("X", "user_anabel")
            assert exc.value.status_code == 400

    def test_add_member_to_house(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        with patch("app.services.home.house_invitation_repository") as mock_inv, \
             patch("app.services.home.house_repository") as mock_h, \
             patch("app.services.home.supabase"):
            mock_inv.find_unused_by_code.return_value = {
                "id": "inv-1", "code": "DEMO2026", "house_id": "casa_demo", "expires_at": future,
            }
            mock_h.find_by_id.return_value = {"id": "casa_demo", "name": "Casa Demo"}
            assert home_service.consume_invitation_code("DEMO2026", "user_anabel")["id"] == "casa_demo"

    @pytest.mark.parametrize("house_id, house, expected", [
        (None, None, None),
        ("casa_demo", {"id": "casa_demo"}, None),
    ])
    def test_returns_none_when_missing_house_or_token(self, house_id, house, expected):
        with patch("app.services.home.house_member_repository") as mock_hm, \
             patch("app.services.home.house_repository") as mock_h:
            mock_hm.find_house_id_by_user.return_value = house_id
            mock_h.find_by_id.return_value = house
            assert home_service.get_bot_target_for_user("user_anabel") is expected

    def test_bot_jid_includes_resource_from_token(self):
        with patch("app.services.home.house_member_repository") as mock_hm, \
             patch("app.services.home.house_repository") as mock_h, \
             patch("app.core.config.settings") as mock_s:
            mock_hm.find_house_id_by_user.return_value = "casa_demo"
            mock_h.find_by_id.return_value = {"id": "casa_demo", "bot_token_hash": "demo2026abcdef00"}
            mock_s.XMPP_BOT_JID = "cano-bot@xmpp.cano-app.com"
            result = home_service.get_bot_target_for_user("user_anabel")
        assert "cano-bot@xmpp.cano-app.com" in result and "bot-demo2026abcd" in result

    def test_user_already_member(self):
        with patch("app.services.home.get_house_id_for_user", return_value="casa_previa"), \
             pytest.raises(HTTPException) as exc:
            home_service.setup_house("user_anabel", "Casa Demo")
        assert exc.value.status_code == 409

    def test_full_flow_returns_house_id_and_token(self):
        with patch("app.services.home.get_house_id_for_user", return_value=None), \
             patch("app.services.home.supabase") as mock_db:
            houses_chain = MagicMock()
            houses_chain.execute.return_value.data = [{"id": "casa_nueva"}]

            def table_side(name):
                m = MagicMock()
                if name == "houses":
                    m.insert.return_value = houses_chain
                else:
                    m.insert.return_value.execute.return_value = MagicMock()
                m.delete.return_value.eq.return_value.execute.return_value = MagicMock()
                return m
            mock_db.table.side_effect = table_side

            result = home_service.setup_house("user_anabel", "Casa Demo")
        assert result["house_id"] == "casa_nueva" and isinstance(result["bot_token"], str)

    def test_rolls_back_house_when_member_insert_fails(self):
        with patch("app.services.home.get_house_id_for_user", return_value=None), \
             patch("app.services.home.supabase") as mock_db:
            houses_chain = MagicMock()
            houses_chain.execute.return_value.data = [{"id": "casa_nueva"}]

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
                home_service.setup_house("user_anabel", "Casa Demo")
            calls = [c.args[0] for c in mock_db.table.call_args_list]
            assert calls.count("houses") >= 2

    def test_leave_without_house_is_noop(self):
        with patch("app.services.home.get_house_id_for_user", return_value=None):
            home_service.leave_house("user_anabel")

    def test_deletes_house_when_last_member_leaves(self):
        with patch("app.services.home.get_house_id_for_user", return_value="casa_demo"), \
             patch("app.services.home.get_user_role", return_value="owner"), \
             patch("app.services.home.supabase") as mock_db:
            remaining_chain = MagicMock()
            remaining_chain.execute.return_value.data = []

            def table_side(_name):
                m = MagicMock()
                m.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
                m.delete.return_value.eq.return_value.execute.return_value = MagicMock()
                m.select.return_value.eq.return_value.execute.return_value.data = []
                return m
            mock_db.table.side_effect = table_side

            home_service.leave_house("user_anabel")
            tables_called = [c.args[0] for c in mock_db.table.call_args_list]
            assert "houses" in tables_called

    def test_owner_leaving_transfers_ownership(self):
        with patch("app.services.home.get_house_id_for_user", return_value="casa_demo"), \
             patch("app.services.home.get_user_role", return_value="owner"), \
             patch("app.services.home.supabase") as mock_db:
            update_calls = {}

            def table_side(_name):
                m = MagicMock()
                m.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()
                m.select.return_value.eq.return_value.execute.return_value.data = [
                    {"user_id": "user_carlos"}, {"user_id": "user_marina"},
                ]
                update_chain = MagicMock()
                update_chain.eq.return_value.eq.return_value.execute.return_value = MagicMock()
                m.update.return_value = update_chain
                update_calls["update"] = m.update
                return m
            mock_db.table.side_effect = table_side

            home_service.leave_house("user_anabel")
            update_calls["update"].assert_called_with({"role": "owner"})

    def test_member_cannot_delete_room(self):
        with patch("app.services.home.get_user_role", return_value="member"):
            with pytest.raises(HTTPException) as exc:
                home_service.delete_room("user_anabel", "floor_baja", "room_salon")
        assert exc.value.status_code == 403

    def test_delete_floor_requires_owner_and_existing_house(self):
        with patch("app.services.home.get_user_house", return_value=None):
            with pytest.raises(HTTPException) as exc:
                home_service.delete_floor("user_anabel", "floor_baja")
        assert exc.value.status_code == 404

        with patch("app.services.home.get_user_house", return_value={"id": "casa_demo"}), \
             patch("app.services.home.get_user_role", return_value="member"):
            with pytest.raises(HTTPException) as exc:
                home_service.delete_floor("user_anabel", "floor_baja")
        assert exc.value.status_code == 403

    def test_get_rooms_by_house_flattens_all_rooms_with_floor(self):
        with patch("app.services.home._get_floors_by_house",
                   return_value=[{"id": "floor_baja", "name": "Planta Baja"}]), \
             patch("app.services.home._get_rooms_by_floor",
                   return_value=[{"id": "room_salon", "name": "Salon"}, {"id": "room_cocina", "name": "Cocina"}]):
            rooms = home_service.get_rooms_by_house("casa_demo")
        assert len(rooms) == 2 and all(r["floor_name"] == "Planta Baja" for r in rooms)

    def test_create_room(self):
        with patch("app.services.home.supabase") as mock_db:
            mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "room_cocina", "name": "Cocina"}],
            )
            room = home_service.create_room("floor_baja", "Cocina")
        assert room["id"] == "room_cocina"
