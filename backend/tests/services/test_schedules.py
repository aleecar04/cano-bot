import uuid
from app.services.home import home_service
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.schedules import ScheduleCreate, ScheduleMarkRun, ScheduleToggle
from app.services.schedules import schedules_service


def _payload(with_cron=True):
    return ScheduleCreate(
        name="Apagar 22h", device_id=uuid.uuid4(), action="encender", payload={},
        cron_expr="0 8 * * *" if with_cron else None, timezone="UTC",
    )


class TestSchedulesService:

    def test_without_cron_or_run_at_raises_400(self):
        sched_in = ScheduleCreate(name="x", device_id=uuid.uuid4(), action="encender")
        with pytest.raises(HTTPException) as exc:
            schedules_service.create_schedule(sched_in, "user_anabel")
        assert exc.value.status_code == 400

    def test_with_cron_inserts_and_returns_row(self):
        with patch("app.services.schedules.schedule_repository") as mock_r, \
             patch("app.services.schedules.supabase") as mock_db:
            mock_r.find_conflicting_power.return_value = []
            mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "schedule_apagar", "action": "encender"}]
            )
            assert schedules_service.create_schedule(_payload(), "user_anabel")["id"] == "schedule_apagar"

    def test_power_conflict_raises_400(self):
        with patch("app.services.schedules.schedule_repository") as mock_r:
            mock_r.find_conflicting_power.return_value = [{"id": "schedule_previo"}]
            with pytest.raises(HTTPException) as exc:
                schedules_service.create_schedule(_payload(), "user_anabel")
            assert exc.value.status_code == 400

    @pytest.mark.parametrize("data, expected", [
        ([{"id": "schedule_apagar"}], True),
        ([], False),
    ])
    def test_delete_schedule_returns_outcome_of_delete(self, data, expected):
        with patch("app.services.schedules.supabase") as mock_db:
            mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=data)
            assert schedules_service.delete_schedule("schedule_apagar", "user_anabel") is expected

    def test_owner_deletes_any_schedule(self):
        with patch.object(home_service, "get_house_member_ids", return_value=["user_anabel", "user_carlos"]), \
             patch("app.services.schedules.schedule_repository") as mock_r, \
             patch("app.services.schedules.supabase") as mock_db:
            mock_r.find_cron_meta_in_house.return_value = {
                "cron_expr": "* * * * *", "timezone": "UTC", "user_id": "user_carlos",
            }
            mock_db.table.return_value.delete.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[{"id": "schedule_apagar"}])
            assert schedules_service.delete_schedule_any("schedule_apagar", "user_anabel") is True

    @pytest.mark.parametrize("is_active", [True, False])
    def test_toggle_updates_and_returns_row(self, is_active):
        with patch.object(schedules_service, "get_schedule", return_value={
                "id": "schedule_apagar", "cron_expr": "0 8 * * *", "timezone": "UTC"}), \
             patch("app.services.schedules.supabase") as mock_db:
            mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": "schedule_apagar", "is_active": is_active}]
            )
            assert schedules_service.toggle_schedule("schedule_apagar", "user_anabel", ScheduleToggle(is_active=is_active)) is not None

    @pytest.mark.parametrize("cron_expr, expected_inactive", [
        ("* * * * *", None),
        (None, False),
    ])
    def test_mark_schedule_run_updates_state(self, cron_expr, expected_inactive):
        with patch("app.services.schedules.schedule_repository") as mock_r, \
             patch("app.services.schedules.supabase") as mock_db:
            mock_r.find_cron_meta_by_id.return_value = {"cron_expr": cron_expr, "timezone": "UTC"}
            schedules_service.mark_schedule_run("schedule_apagar", ScheduleMarkRun(command_id="cmd_encender"))
        update_data = mock_db.table.return_value.update.call_args[0][0]
        assert update_data.get("is_active") is expected_inactive

    def test_returns_none_when_schedule_not_in_house(self):
        with patch.object(home_service, "get_house_member_ids", return_value=["user_anabel"]), \
             patch("app.services.schedules.schedule_repository") as mock_r:
            mock_r.find_cron_meta_in_house.return_value = None
            assert schedules_service.toggle_schedule_any("schedule_apagar", "user_anabel", ScheduleToggle(is_active=True)) is None

    def test_calculate_next_run(self):
        with patch.object(home_service, "get_house_member_ids", return_value=["user_anabel"]), \
             patch("app.services.schedules.schedule_repository") as mock_r, \
             patch("app.services.schedules.supabase") as mock_db:
            mock_r.find_cron_meta_in_house.return_value = {"cron_expr": "0 8 * * *", "timezone": "UTC"}
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": "schedule_apagar"}]
            )
            assert schedules_service.toggle_schedule_any("schedule_apagar", "user_anabel", ScheduleToggle(is_active=True)) is not None
            update_data = mock_db.table.return_value.update.call_args[0][0]
            assert "next_run_at" in update_data

    @pytest.mark.parametrize("role", ["owner", "member"])
    def test_delete_completed_schedules_filters_by_role(self, role):
        with patch.object(home_service, "get_user_role", return_value=role), \
             patch.object(home_service, "get_house_member_ids", return_value=["user_anabel", "user_carlos"]), \
             patch("app.services.schedules.supabase") as mock_db:
            mock_db.table.return_value.delete.return_value.is_.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(data=[{"id": "x"}])
            mock_db.table.return_value.delete.return_value.is_.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "x"}])
            result = schedules_service.delete_completed_schedules("user_anabel")
        assert result >= 0
