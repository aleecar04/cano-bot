import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.command_executor import CommandSource, ScheduleSource, execute_command


@contextmanager
def _patched_deps(device=None, send=None):
    with patch("app.services.command_executor.xmpp_account_repository") as mock_x, \
         patch("app.services.command_executor.get_bot_target_for_user", return_value="cano-bot@xmpp.cano-app.com"), \
         patch("app.services.command_executor.supabase") as mock_db, \
         patch("app.services.command_executor.get_house_id_for_user", return_value="casa_demo"), \
         patch("app.services.command_executor.device_repository") as mock_d, \
         patch("app.services.command_executor.send_xmpp_message", new_callable=AsyncMock) as mock_send:
        mock_x.find_jid_by_user.return_value = "anabel@xmpp.cano-app.com"
        mock_db.rpc.return_value.execute.return_value.data = "CanoBot2026!"
        mock_d.find_by_id_and_house.return_value = device
        if send is not None:
            mock_send.side_effect = send
        chain = MagicMock()
        chain.execute.return_value.data = [{"id": "cmd_nuevo"}]
        mock_db.table.return_value.insert.return_value = chain
        yield mock_db, mock_send


class TestCommandExecutor:

    def test_schedule_source_marks_run_on_post_execute(self):
        s = ScheduleSource(schedule_id="schedule_apagar")
        assert s.source_type == "schedule" and s.source_id == "schedule_apagar"
        with patch("app.services.schedules.mark_schedule_run") as mock_mark:
            s.post_execute("schedule_apagar", "cmd_encender")
        mock_mark.assert_called_once()

    def test_execute_command_with_unknown_device_raises_404(self):
        with _patched_deps(device=None), pytest.raises(HTTPException) as exc:
            asyncio.run(execute_command(
                action="encender", payload={}, user_id="user_anabel",
                source=CommandSource(), device_id="device_fantasma",
            ))
        assert exc.value.status_code == 404

    @pytest.mark.parametrize("device_type, payload", [
        ("Enchufe", {"value": 50}),
        ("Luz", {"value": 150}),
    ])
    def test_execute_command_invalid_action_or_payload_raises_409(self, device_type, payload):
        device = {"id": "device_lampara", "name": device_type, "type": device_type}
        with _patched_deps(device=device), pytest.raises(HTTPException) as exc:
            asyncio.run(execute_command(
                action="brillo", payload=payload, user_id="user_anabel",
                source=CommandSource(), device_id="device_lampara",
            ))
        assert exc.value.status_code == 409

    def test_execute_command_system_returns_command_id(self):
        with _patched_deps():
            result = asyncio.run(execute_command(
                action="scan", payload={}, user_id="user_anabel",
                source=CommandSource(), device_id=None,
            ))
        assert result == {"ok": True, "command_id": "cmd_nuevo"}

    def test_execute_command_without_xmpp_account_raises_404(self):
        with patch("app.services.command_executor.xmpp_account_repository") as mock_x:
            mock_x.find_jid_by_user.return_value = None
            with pytest.raises(HTTPException) as exc:
                asyncio.run(execute_command(
                    action="scan", payload={}, user_id="user_anabel",
                    source=CommandSource(), device_id=None,
                ))
        assert exc.value.status_code == 404

    def test_execute_command_without_bot_target_raises_400(self):
        with patch("app.services.command_executor.xmpp_account_repository") as mock_x, \
             patch("app.services.command_executor.get_bot_target_for_user", return_value=None), \
             patch("app.services.command_executor.supabase") as mock_db:
            mock_x.find_jid_by_user.return_value = "anabel@xmpp.cano-app.com"
            mock_db.rpc.return_value.execute.return_value.data = "CanoBot2026!"
            with pytest.raises(HTTPException) as exc:
                asyncio.run(execute_command(
                    action="scan", payload={}, user_id="user_anabel",
                    source=CommandSource(), device_id=None,
                ))
        assert exc.value.status_code == 400

    def test_execute_command_propagates_xmpp_error(self):
        def boom(**_kw):
            raise RuntimeError("xmpp down")
        with _patched_deps(send=boom), pytest.raises(RuntimeError):
            asyncio.run(execute_command(
                action="scan", payload={}, user_id="user_anabel",
                source=CommandSource(), device_id=None,
            ))
