from unittest.mock import MagicMock, patch
from fastapi import HTTPException
import pytest

from app.services import commands as cmd_service


# ── get_command_history ──────────────────────────────────────────────────────

class TestGetCommandHistory:

    def test_member_solo_ve_lo_suyo(self):
        with patch("app.services.commands.get_user_role", return_value="member"), \
             patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_history.return_value = []
            cmd_service.get_command_history("u1", member_id="u2")
        called = mock_repo.find_history.call_args
        assert called.kwargs["user_ids"] == "u1"

    def test_owner_con_all_devuelve_todos_los_miembros(self):
        with patch("app.services.commands.get_user_role", return_value="owner"), \
             patch("app.services.commands.get_house_member_ids", return_value=["u1", "u2"]), \
             patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_history.return_value = []
            cmd_service.get_command_history("u1", member_id="all")
        called = mock_repo.find_history.call_args
        assert called.kwargs["user_ids"] == ["u1", "u2"]

    def test_owner_con_member_id_valido_lo_usa(self):
        with patch("app.services.commands.get_user_role", return_value="owner"), \
             patch("app.services.commands.get_house_member_ids", return_value=["u2"]), \
             patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_history.return_value = []
            cmd_service.get_command_history("u1", member_id="u2")
        called = mock_repo.find_history.call_args
        assert called.kwargs["user_ids"] == "u2"

    def test_owner_con_member_id_inválido_filtra_a_si_mismo(self):
        with patch("app.services.commands.get_user_role", return_value="owner"), \
             patch("app.services.commands.get_house_member_ids", return_value=["u1"]), \
             patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_history.return_value = []
            cmd_service.get_command_history("u1", member_id="u2")
        called = mock_repo.find_history.call_args
        assert called.kwargs["user_ids"] == "u1"


# ── get_command_by_id ────────────────────────────────────────────────────────

class TestGetCommandById:

    def test_encontrado_devuelve_command(self):
        with patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_by_id_and_user.return_value = {"id": "c1"}
            assert cmd_service.get_command_by_id("c1", "u1") == {"id": "c1"}

    def test_no_encontrado_lanza_404(self):
        with patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_by_id_and_user.return_value = None
            with pytest.raises(HTTPException) as exc:
                cmd_service.get_command_by_id("ghost", "u1")
            assert exc.value.status_code == 404


# ── create_command_from_bot ─────────────────────────────────────────────────

class TestCreateCommandFromBot:

    def test_user_de_otra_casa_lanza_403(self):
        with patch("app.services.commands.house_member_repository") as mock_h:
            mock_h.find_house_id_by_user.return_value = "h_otra"
            with pytest.raises(HTTPException) as exc:
                cmd_service.create_command_from_bot({
                    "_authenticated_house_id": "h1",
                    "user_id": "u1",
                    "action": "ayuda",
                })
            assert exc.value.status_code == 403

    def test_pending_marca_status_pending(self):
        with patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_h.find_house_id_by_user.return_value = "h1"
            mock_chain = MagicMock()
            mock_chain.execute.return_value.data = [{"id": "c_new"}]
            mock_db.table.return_value.insert.return_value = mock_chain
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
            result = cmd_service.create_command_from_bot({
                "_authenticated_house_id": "h1",
                "user_id": "u1",
                "action": "ayuda",
                "pending": True,
            })
        assert result["command_id"] == "c_new"
        insert_data = mock_db.table.return_value.insert.call_args[0][0]
        assert insert_data["status"] == "pending"

    def test_error_marca_status_failed(self):
        with patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_h.find_house_id_by_user.return_value = "h1"
            mock_chain = MagicMock()
            mock_chain.execute.return_value.data = [{"id": "c_new"}]
            mock_db.table.return_value.insert.return_value = mock_chain
            cmd_service.create_command_from_bot({
                "_authenticated_house_id": "h1",
                "user_id": "u1",
                "action": "encender",
                "device_id": "d1",
                "error": "timeout",
            })
        insert_data = mock_db.table.return_value.insert.call_args[0][0]
        assert insert_data["status"] == "failed"

    def test_sin_error_marca_executed(self):
        with patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_h.find_house_id_by_user.return_value = "h1"
            mock_chain = MagicMock()
            mock_chain.execute.return_value.data = [{"id": "c_new"}]
            mock_db.table.return_value.insert.return_value = mock_chain
            cmd_service.create_command_from_bot({
                "_authenticated_house_id": "h1",
                "user_id": "u1",
                "action": "ayuda",
            })
        insert_data = mock_db.table.return_value.insert.call_args[0][0]
        assert insert_data["status"] == "executed"

    def test_deduce_target_type_device_si_device_id(self):
        with patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_h.find_house_id_by_user.return_value = "h1"
            mock_chain = MagicMock()
            mock_chain.execute.return_value.data = [{"id": "c_new"}]
            mock_db.table.return_value.insert.return_value = mock_chain
            cmd_service.create_command_from_bot({
                "_authenticated_house_id": "h1",
                "user_id": "u1",
                "action": "encender",
                "device_id": "d1",
            })
        insert_data = mock_db.table.return_value.insert.call_args[0][0]
        assert insert_data["target_type"] == "device"

    def test_deduce_target_type_info_para_ayuda(self):
        with patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_h.find_house_id_by_user.return_value = "h1"
            mock_chain = MagicMock()
            mock_chain.execute.return_value.data = [{"id": "c_new"}]
            mock_db.table.return_value.insert.return_value = mock_chain
            cmd_service.create_command_from_bot({
                "_authenticated_house_id": "h1",
                "user_id": "u1",
                "action": "ayuda",
            })
        insert_data = mock_db.table.return_value.insert.call_args[0][0]
        assert insert_data["target_type"] == "info"


# ── update_command_result ────────────────────────────────────────────────────

class TestUpdateCommandResult:

    def test_command_no_existe_404(self):
        with patch("app.services.commands.command_repository") as mock_repo:
            mock_repo.find_meta_by_id.return_value = None
            with pytest.raises(HTTPException) as exc:
                cmd_service.update_command_result("c1", "h1", None)
            assert exc.value.status_code == 404

    def test_command_de_otra_casa_403(self):
        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h:
            mock_repo.find_meta_by_id.return_value = {"user_id": "u1"}
            mock_h.find_house_id_by_user.return_value = "h_otra"
            with pytest.raises(HTTPException) as exc:
                cmd_service.update_command_result("c1", "h1", None)
            assert exc.value.status_code == 403

    def test_actualiza_con_executed(self):
        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_repo.find_meta_by_id.return_value = {"user_id": "u1", "source_type": "direct"}
            mock_h.find_house_id_by_user.return_value = "h1"
            cmd_service.update_command_result("c1", "h1", None, {"x": 1})
        update_data = mock_db.table.return_value.update.call_args[0][0]
        assert update_data["status"] == "executed"
        assert update_data["result_data"] == {"x": 1}

    def test_actualiza_con_failed_si_error(self):
        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase") as mock_db:
            mock_repo.find_meta_by_id.return_value = {"user_id": "u1", "source_type": "direct"}
            mock_h.find_house_id_by_user.return_value = "h1"
            cmd_service.update_command_result("c1", "h1", "timeout")
        update_data = mock_db.table.return_value.update.call_args[0][0]
        assert update_data["status"] == "failed"
        assert update_data["error"] == "timeout"

    def test_schedule_dispara_push(self):
        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase"), \
             patch("app.services.commands.send_push") as mock_push:
            mock_repo.find_meta_by_id.return_value = {
                "user_id": "u1", "source_type": "schedule",
                "action": "encender", "devices": {"name": "Luz"},
            }
            mock_h.find_house_id_by_user.return_value = "h1"
            cmd_service.update_command_result("c1", "h1", None)
        mock_push.assert_called_once()

    def test_push_excepcion_no_rompe(self):
        with patch("app.services.commands.command_repository") as mock_repo, \
             patch("app.services.commands.house_member_repository") as mock_h, \
             patch("app.services.commands.supabase"), \
             patch("app.services.commands.send_push", side_effect=Exception("boom")):
            mock_repo.find_meta_by_id.return_value = {
                "user_id": "u1", "source_type": "schedule", "action": "encender",
            }
            mock_h.find_house_id_by_user.return_value = "h1"
            cmd_service.update_command_result("c1", "h1", None)  # no debe lanzar
