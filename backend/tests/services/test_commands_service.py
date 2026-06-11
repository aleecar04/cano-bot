from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import commands as cmd_service


class TestCommandsService:

    @pytest.mark.parametrize("role, member_ids, member_id_arg, expected_user_ids", [
        ("member", None, "user_carlos", "user_anabel"),
        ("owner", ["user_anabel", "user_carlos"], "all", ["user_anabel", "user_carlos"]),
        ("owner", ["user_carlos"], "user_carlos", "user_carlos"),
    ])
    def test_history_filtered_by_role(self, role, member_ids, member_id_arg, expected_user_ids):
        with patch("app.services.commands.get_user_role", return_value=role), \
             patch("app.services.commands.get_house_member_ids", return_value=member_ids or []), \
             patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_history.return_value = []
            cmd_service.get_command_history("user_anabel", member_id=member_id_arg)
        assert mock_repo.find_history.call_args.kwargs["user_ids"] == expected_user_ids

    def test_get_command_by_id_returns_command_or_raises_404(self):
        with patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_by_id_and_user.return_value = {"id": "cmd_encender"}
            assert cmd_service.get_command_by_id("cmd_encender", "user_anabel") == {"id": "cmd_encender"}

        with patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_by_id_and_user.return_value = None
            with pytest.raises(HTTPException) as exc:
                cmd_service.get_command_by_id("fantasma", "user_anabel")
            assert exc.value.status_code == 404

    def test_user_from_other_house_raises_403(self):
        with patch("app.services.commands.house_member_repository") as mock_h:
            mock_h.find_house_id_by_user.return_value = "otra_casa"
            with pytest.raises(HTTPException) as exc:
                cmd_service.create_command_from_bot({
                    "_authenticated_house_id": "casa_demo", "user_id": "user_anabel", "action": "ayuda",
                })
            assert exc.value.status_code == 403

    @pytest.mark.parametrize("payload_extra, expected_status, expected_target", [
        ({"pending": True}, "pending", "info"),
        ({"device_id": "device_lampara", "error": "timeout"}, "failed", "device"),
        ({"device_id": "device_lampara"}, "executed", "device"),
    ])
    def test_status_and_target_inferred_from_payload(self, payload_extra, expected_status, expected_target):
        with patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_h.find_house_id_by_user.return_value = "casa_demo"
            chain = MagicMock()
            chain.execute.return_value.data = [{"id": "cmd_nuevo"}]
            mock_db.table.return_value.insert.return_value = chain
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
            cmd_service.create_command_from_bot({
                "_authenticated_house_id": "casa_demo", "user_id": "user_anabel",
                "action": "encender" if "device_id" in payload_extra else "ayuda",
                **payload_extra,
            })
        data = mock_db.table.return_value.insert.call_args[0][0]
        assert data["status"] == expected_status and data["target_type"] == expected_target

    def test_missing_command_raises_404(self):
        with patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_meta_by_id.return_value = None
            with pytest.raises(HTTPException) as exc:
                cmd_service.update_command_result("cmd_encender", "casa_demo", None)
            assert exc.value.status_code == 404

    @pytest.mark.parametrize("error, expected_status", [
        (None, "executed"),
        ("timeout", "failed"),
    ])
    def test_status_failed_when_error_present(self, error, expected_status):
        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_repo.find_meta_by_id.return_value = {"user_id": "user_anabel", "source_type": "direct"}
            mock_h.find_house_id_by_user.return_value = "casa_demo"
            cmd_service.update_command_result("cmd_encender", "casa_demo", error, {"x": 1})
        update = mock_db.table.return_value.update.call_args[0][0]
        assert update["status"] == expected_status

    def test_schedule_pushes_and_ignores_push_errors(self):
        meta = {"user_id": "user_anabel", "source_type": "schedule", "action": "encender",
                "devices": {"name": "Lampara Salon"}}
        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase"), \
             patch("app.services.commands.send_push") as mock_push:
            mock_repo.find_meta_by_id.return_value = meta
            mock_h.find_house_id_by_user.return_value = "casa_demo"
            cmd_service.update_command_result("cmd_encender", "casa_demo", None)
        mock_push.assert_called_once()

        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase"), \
             patch("app.services.commands.send_push", side_effect=Exception("boom")):
            mock_repo.find_meta_by_id.return_value = meta
            mock_h.find_house_id_by_user.return_value = "casa_demo"
            cmd_service.update_command_result("cmd_encender", "casa_demo", None)
