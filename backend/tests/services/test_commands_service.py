from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import commands as cmd_service


# ── get_command_history ──────────────────────────────────────────────────────

class TestGetCommandHistory:

    @pytest.mark.parametrize("role, member_ids, member_id_arg, expected_user_ids", [
        ("member", None, "u2", "u1"),                       # member always sees own
        ("owner", ["u1", "u2"], "all", ["u1", "u2"]),       # owner+all → all members
        ("owner", ["u2"], "u2", "u2"),                      # owner+valid id → that id
        ("owner", ["u1"], "u2", "u1"),                      # owner+invalid id → own
    ])
    def test_user_ids_filter_depends_on_role_and_member_arg(self, role, member_ids, member_id_arg, expected_user_ids):
        with patch("app.services.commands.get_user_role", return_value=role), \
             patch("app.services.commands.get_house_member_ids", return_value=member_ids or []), \
             patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_history.return_value = []
            cmd_service.get_command_history("u1", member_id=member_id_arg)
        assert mock_repo.find_history.call_args.kwargs["user_ids"] == expected_user_ids


# ── get_command_by_id ────────────────────────────────────────────────────────

def test_get_command_by_id_returns_command_or_raises_404():
    with patch("app.services.commands.command_repository") as mock_repo:
        mock_repo.find_by_id_and_user.return_value = {"id": "c1"}
        assert cmd_service.get_command_by_id("c1", "u1") == {"id": "c1"}

    with patch("app.services.commands.command_repository") as mock_repo:
        mock_repo.find_by_id_and_user.return_value = None
        with pytest.raises(HTTPException) as exc:
            cmd_service.get_command_by_id("ghost", "u1")
        assert exc.value.status_code == 404


# ── create_command_from_bot ─────────────────────────────────────────────────

class TestCreateCommandFromBot:

    def _patch_insert(self):
        return patch("app.services.commands.supabase")

    def test_user_from_other_house_raises_403(self):
        with patch("app.services.commands.house_member_repository") as mock_h:
            mock_h.find_house_id_by_user.return_value = "h_otra"
            with pytest.raises(HTTPException) as exc:
                cmd_service.create_command_from_bot({
                    "_authenticated_house_id": "h1", "user_id": "u1", "action": "ayuda",
                })
            assert exc.value.status_code == 403

    @pytest.mark.parametrize("payload_extra, expected_status, expected_target", [
        ({"pending": True}, "pending", "info"),
        ({"device_id": "d1", "error": "timeout"}, "failed", "device"),
        ({}, "executed", "info"),
        ({"device_id": "d1"}, "executed", "device"),
    ])
    def test_status_and_target_type_inferred_from_payload(self, payload_extra, expected_status, expected_target):
        with patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_h.find_house_id_by_user.return_value = "h1"
            chain = MagicMock()
            chain.execute.return_value.data = [{"id": "c_new"}]
            mock_db.table.return_value.insert.return_value = chain
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
            cmd_service.create_command_from_bot({
                "_authenticated_house_id": "h1", "user_id": "u1",
                "action": "encender" if "device_id" in payload_extra else "ayuda",
                **payload_extra,
            })
        data = mock_db.table.return_value.insert.call_args[0][0]
        assert data["status"] == expected_status and data["target_type"] == expected_target


# ── update_command_result ────────────────────────────────────────────────────

class TestUpdateCommandResult:

    def test_missing_command_raises_404(self):
        with patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_meta_by_id.return_value = None
            with pytest.raises(HTTPException) as exc:
                cmd_service.update_command_result("c1", "h1", None)
            assert exc.value.status_code == 404

    def test_command_from_other_house_raises_403(self):
        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h:
            mock_repo.find_meta_by_id.return_value = {"user_id": "u1"}
            mock_h.find_house_id_by_user.return_value = "h_otra"
            with pytest.raises(HTTPException) as exc:
                cmd_service.update_command_result("c1", "h1", None)
            assert exc.value.status_code == 403

    @pytest.mark.parametrize("error, expected_status", [
        (None, "executed"),
        ("timeout", "failed"),
    ])
    def test_status_reflects_presence_of_error(self, error, expected_status):
        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_repo.find_meta_by_id.return_value = {"user_id": "u1", "source_type": "direct"}
            mock_h.find_house_id_by_user.return_value = "h1"
            cmd_service.update_command_result("c1", "h1", error, {"x": 1})
        update = mock_db.table.return_value.update.call_args[0][0]
        assert update["status"] == expected_status

    def test_schedule_triggers_push_and_swallows_push_errors(self):
        meta = {"user_id": "u1", "source_type": "schedule", "action": "encender",
                "devices": {"name": "Luz"}}
        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase"), \
             patch("app.services.commands.send_push") as mock_push:
            mock_repo.find_meta_by_id.return_value = meta
            mock_h.find_house_id_by_user.return_value = "h1"
            cmd_service.update_command_result("c1", "h1", None)
        mock_push.assert_called_once()

        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase"), \
             patch("app.services.commands.send_push", side_effect=Exception("boom")):
            mock_repo.find_meta_by_id.return_value = meta
            mock_h.find_house_id_by_user.return_value = "h1"
            cmd_service.update_command_result("c1", "h1", None)
