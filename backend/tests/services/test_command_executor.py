from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
import pytest

from app.services.command_executor import (
    CommandSource, ScheduleSource, execute_command,
)


class TestCommandSource:

    def test_default_es_direct(self):
        s = CommandSource()
        assert s.source_type == "direct"
        assert s.source_id is None

    def test_post_execute_no_hace_nada(self):
        CommandSource().post_execute(None, "c1")  # solo verificar que no lanza


class TestScheduleSource:

    def test_source_type_es_schedule(self):
        s = ScheduleSource(schedule_id="s1")
        assert s.source_type == "schedule"
        assert s.source_id == "s1"

    def test_post_execute_marca_schedule_run(self):
        s = ScheduleSource(schedule_id="s1")
        with patch("app.services.schedules.mark_schedule_run") as mock_mark:
            s.post_execute("s1", "c1")
        mock_mark.assert_called_once()


class TestExecuteCommand:

    def test_device_no_existente_lanza_404(self):
        with patch("app.services.command_executor.xmpp_account_repository") as mock_x, \
             patch("app.services.command_executor.get_bot_target_for_user", return_value="bot@x"), \
             patch("app.services.command_executor.supabase") as mock_db, \
             patch("app.services.command_executor.get_house_id_for_user", return_value="h1"), \
             patch("app.services.command_executor.device_repository") as mock_d:
            mock_x.find_jid_by_user.return_value = "u@x"
            mock_db.rpc.return_value.execute.return_value.data = "pwd"
            mock_d.find_by_id_and_house.return_value = None
            with pytest.raises(HTTPException) as exc:
                import asyncio
                asyncio.run(execute_command(
                    action="encender", payload={}, user_id="u1",
                    source=CommandSource(), device_id="d_no_existe",
                ))
            assert exc.value.status_code == 404

    def test_accion_no_soportada_lanza_409(self):
        with patch("app.services.command_executor.xmpp_account_repository") as mock_x, \
             patch("app.services.command_executor.get_bot_target_for_user", return_value="bot@x"), \
             patch("app.services.command_executor.supabase") as mock_db, \
             patch("app.services.command_executor.get_house_id_for_user", return_value="h1"), \
             patch("app.services.command_executor.device_repository") as mock_d:
            mock_x.find_jid_by_user.return_value = "u@x"
            mock_db.rpc.return_value.execute.return_value.data = "pwd"
            mock_d.find_by_id_and_house.return_value = {"id": "d1", "name": "Enchufe", "type": "Enchufe"}
            with pytest.raises(HTTPException) as exc:
                import asyncio
                asyncio.run(execute_command(
                    action="brillo", payload={"valor": 50}, user_id="u1",
                    source=CommandSource(), device_id="d1",
                ))
            assert exc.value.status_code == 409

    def test_payload_invalido_lanza_409(self):
        with patch("app.services.command_executor.xmpp_account_repository") as mock_x, \
             patch("app.services.command_executor.get_bot_target_for_user", return_value="bot@x"), \
             patch("app.services.command_executor.supabase") as mock_db, \
             patch("app.services.command_executor.get_house_id_for_user", return_value="h1"), \
             patch("app.services.command_executor.device_repository") as mock_d:
            mock_x.find_jid_by_user.return_value = "u@x"
            mock_db.rpc.return_value.execute.return_value.data = "pwd"
            mock_d.find_by_id_and_house.return_value = {"id": "d1", "name": "Luz", "type": "Luz"}
            with pytest.raises(HTTPException) as exc:
                import asyncio
                asyncio.run(execute_command(
                    action="brillo", payload={"valor": 150}, user_id="u1",
                    source=CommandSource(), device_id="d1",
                ))
            assert exc.value.status_code == 409

    def test_xmpp_falla_marca_command_error(self):
        import asyncio
        with patch("app.services.command_executor.xmpp_account_repository") as mock_x, \
             patch("app.services.command_executor.get_bot_target_for_user", return_value="bot@x"), \
             patch("app.services.command_executor.supabase") as mock_db, \
             patch("app.services.command_executor.get_house_id_for_user", return_value="h1"), \
             patch("app.services.command_executor.device_repository") as mock_d, \
             patch("app.services.command_executor.send_xmpp_message", new_callable=AsyncMock) as mock_send:
            mock_x.find_jid_by_user.return_value = "u@x"
            mock_db.rpc.return_value.execute.return_value.data = "pwd"
            mock_d.find_by_id_and_house.return_value = {"id": "d1", "name": "Luz", "type": "Luz"}
            mock_chain = MagicMock()
            mock_chain.execute.return_value.data = [{"id": "c_new"}]
            mock_db.table.return_value.insert.return_value = mock_chain
            mock_send.side_effect = RuntimeError("xmpp down")
            with pytest.raises(RuntimeError):
                asyncio.run(execute_command(
                    action="encender", payload={}, user_id="u1",
                    source=CommandSource(), device_id="d1",
                ))

    def test_happy_path_system_command(self):
        import asyncio
        with patch("app.services.command_executor.xmpp_account_repository") as mock_x, \
             patch("app.services.command_executor.get_bot_target_for_user", return_value="bot@x"), \
             patch("app.services.command_executor.supabase") as mock_db, \
             patch("app.services.command_executor.send_xmpp_message", new_callable=AsyncMock):
            mock_x.find_jid_by_user.return_value = "u@x"
            mock_db.rpc.return_value.execute.return_value.data = "pwd"
            mock_chain = MagicMock()
            mock_chain.execute.return_value.data = [{"id": "c_new"}]
            mock_db.table.return_value.insert.return_value = mock_chain
            result = asyncio.run(execute_command(
                action="scan", payload={}, user_id="u1",
                source=CommandSource(), device_id=None,
            ))
        assert result == {"ok": True, "command_id": "c_new"}
