import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.command_executor import CommandSource, ScheduleSource, execute_command


@contextmanager
def _patched_deps(device=None, send=None):
    with patch("app.services.command_executor.xmpp_account_repository") as mock_x, \
         patch("app.services.command_executor.get_bot_target_for_user", return_value="bot@x"), \
         patch("app.services.command_executor.supabase") as mock_db, \
         patch("app.services.command_executor.get_house_id_for_user", return_value="h1"), \
         patch("app.services.command_executor.device_repository") as mock_d, \
         patch("app.services.command_executor.send_xmpp_message", new_callable=AsyncMock) as mock_send:
        mock_x.find_jid_by_user.return_value = "u@x"
        mock_db.rpc.return_value.execute.return_value.data = "pwd"
        mock_d.find_by_id_and_house.return_value = device
        if send is not None:
            mock_send.side_effect = send
        chain = MagicMock()
        chain.execute.return_value.data = [{"id": "c_new"}]
        mock_db.table.return_value.insert.return_value = chain
        yield mock_db, mock_send


def test_schedule_source_marks_run_on_post_execute():
    s = ScheduleSource(schedule_id="s1")
    assert s.source_type == "schedule" and s.source_id == "s1"
    with patch("app.services.schedules.mark_schedule_run") as mock_mark:
        s.post_execute("s1", "c1")
    mock_mark.assert_called_once()


def test_execute_command_with_unknown_device_raises_404():
    with _patched_deps(device=None), pytest.raises(HTTPException) as exc:
        asyncio.run(execute_command(
            action="encender", payload={}, user_id="u1",
            source=CommandSource(), device_id="d_no_existe",
        ))
    assert exc.value.status_code == 404


@pytest.mark.parametrize("device_type, payload", [
    ("Enchufe", {"valor": 50}),
    ("Luz", {"valor": 150}),
])
def test_execute_command_invalid_action_or_payload_raises_409(device_type, payload):
    device = {"id": "d1", "name": device_type, "type": device_type}
    with _patched_deps(device=device), pytest.raises(HTTPException) as exc:
        asyncio.run(execute_command(
            action="brillo", payload=payload, user_id="u1",
            source=CommandSource(), device_id="d1",
        ))
    assert exc.value.status_code == 409


def test_execute_command_system_returns_command_id():
    with _patched_deps():
        result = asyncio.run(execute_command(
            action="scan", payload={}, user_id="u1",
            source=CommandSource(), device_id=None,
        ))
    assert result == {"ok": True, "command_id": "c_new"}


def test_execute_command_without_xmpp_account_raises_404():
    with patch("app.services.command_executor.xmpp_account_repository") as mock_x:
        mock_x.find_jid_by_user.return_value = None
        with pytest.raises(HTTPException) as exc:
            asyncio.run(execute_command(
                action="scan", payload={}, user_id="u1",
                source=CommandSource(), device_id=None,
            ))
    assert exc.value.status_code == 404


def test_execute_command_without_bot_target_raises_400():
    with patch("app.services.command_executor.xmpp_account_repository") as mock_x, \
         patch("app.services.command_executor.get_bot_target_for_user", return_value=None), \
         patch("app.services.command_executor.supabase") as mock_db:
        mock_x.find_jid_by_user.return_value = "u@x"
        mock_db.rpc.return_value.execute.return_value.data = "pwd"
        with pytest.raises(HTTPException) as exc:
            asyncio.run(execute_command(
                action="scan", payload={}, user_id="u1",
                source=CommandSource(), device_id=None,
            ))
    assert exc.value.status_code == 400


def test_execute_command_marks_command_as_failed_on_xmpp_error():
    def boom(**_kw):
        raise RuntimeError("xmpp down")
    with _patched_deps(send=boom), pytest.raises(RuntimeError):
        asyncio.run(execute_command(
            action="scan", payload={}, user_id="u1",
            source=CommandSource(), device_id=None,
        ))
