import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import schedules as sched_service


def _payload(with_cron=True):
    from app.models.schedules import ScheduleCreate
    return ScheduleCreate(
        name="Mi tarea", device_id=uuid.uuid4(), action="encender", payload={},
        cron_expr="0 8 * * *" if with_cron else None, timezone="UTC",
    )


# ── _next_run ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("tz", ["UTC", "Inventada/Nowhere"])
def test_next_run_returns_future_datetime_falling_back_to_utc(tz):
    from app.services.schedules import _next_run
    result = _next_run("* * * * *", tz)
    assert result > datetime.now(timezone.utc) and result.tzinfo is not None


# ── create_schedule ─────────────────────────────────────────────────────────

class TestCreateSchedule:

    def test_without_cron_or_run_at_raises_400(self):
        from app.models.schedules import ScheduleCreate
        sched_in = ScheduleCreate(name="x", device_id=uuid.uuid4(), action="encender")
        with pytest.raises(HTTPException) as exc:
            sched_service.create_schedule(sched_in, "u1")
        assert exc.value.status_code == 400

    def test_with_cron_inserts_and_returns_row(self):
        with patch("app.services.schedules.schedule_repository") as mock_r, \
             patch("app.services.schedules.supabase") as mock_db:
            mock_r.find_conflicting_power.return_value = []
            mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "s1", "action": "encender"}]
            )
            assert sched_service.create_schedule(_payload(), "u1")["id"] == "s1"

    def test_power_conflict_raises_400(self):
        with patch("app.services.schedules.schedule_repository") as mock_r:
            mock_r.find_conflicting_power.return_value = [{"id": "s_existente"}]
            with pytest.raises(HTTPException) as exc:
                sched_service.create_schedule(_payload(), "u1")
            assert exc.value.status_code == 400


# ── get_schedules / get_schedule ────────────────────────────────────────────

# ── delete_schedule ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("data, expected", [
    ([{"id": "s1"}], True),
    ([], False),
])
def test_delete_schedule_returns_outcome_of_delete(data, expected):
    with patch("app.services.schedules.supabase") as mock_db:
        mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=data)
        assert sched_service.delete_schedule("s1", "u1") is expected


def test_owner_can_delete_any_schedule_in_house():
    with patch("app.services.schedules.get_house_member_ids", return_value=["u1", "u2"]), \
         patch("app.services.schedules.schedule_repository") as mock_r, \
         patch("app.services.schedules.supabase") as mock_db:
        mock_r.find_cron_meta_in_house.return_value = {
            "cron_expr": "* * * * *", "timezone": "UTC", "user_id": "u2",
        }
        mock_db.table.return_value.delete.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[{"id": "s1"}])
        assert sched_service.delete_schedule_any("s1", "u1") is True


# ── toggle_schedule ─────────────────────────────────────────────────────────

class TestToggleSchedule:

    def _toggle(self, active=True):
        from app.models.schedules import ScheduleToggle
        return ScheduleToggle(is_active=active)

    def test_returns_none_when_schedule_missing(self):
        with patch("app.services.schedules.schedule_repository") as mock_r, \
             patch("app.services.schedules.supabase") as mock_db:
            mock_r.find_by_id_and_user.return_value = None
            mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            assert sched_service.toggle_schedule("ghost", "u1", self._toggle()) is None

    @pytest.mark.parametrize("is_active", [True, False])
    def test_toggle_updates_and_returns_row(self, is_active):
        with patch("app.services.schedules.get_schedule", return_value={
                "id": "s1", "cron_expr": "0 8 * * *", "timezone": "UTC"}), \
             patch("app.services.schedules.supabase") as mock_db:
            mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": "s1", "is_active": is_active}]
            )
            assert sched_service.toggle_schedule("s1", "u1", self._toggle(is_active)) is not None


# ── runner helpers ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("cron_expr, expected_inactive", [
    ("* * * * *", None),     # recurring → still active
    (None, False),           # one-shot → becomes inactive
])
def test_mark_schedule_run_updates_state(cron_expr, expected_inactive):
    from app.models.schedules import ScheduleMarkRun
    with patch("app.services.schedules.schedule_repository") as mock_r, \
         patch("app.services.schedules.supabase") as mock_db:
        mock_r.find_cron_meta_by_id.return_value = {"cron_expr": cron_expr, "timezone": "UTC"}
        sched_service.mark_schedule_run("s1", ScheduleMarkRun(command_id="c1"))
    update_data = mock_db.table.return_value.update.call_args[0][0]
    assert update_data.get("is_active") is expected_inactive
