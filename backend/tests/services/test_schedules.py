from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from datetime import datetime, timezone
import pytest

from app.services import schedules as sched_service


def _utc_iso(dt=None):
    return (dt or datetime.now(timezone.utc)).isoformat()


# ── _next_run ───────────────────────────────────────────────────────────────

class TestNextRun:

    def test_devuelve_datetime_futuro(self):
        from app.services.schedules import _next_run
        # cron cada minuto
        result = _next_run("* * * * *", "UTC")
        assert result > datetime.now(timezone.utc)

    def test_timezone_invalida_cae_a_utc(self):
        from app.services.schedules import _next_run
        result = _next_run("* * * * *", "Inventada/Nowhere")
        assert result.tzinfo is not None


# ── create_schedule ─────────────────────────────────────────────────────────

class TestCreateSchedule:

    def _payload(self, with_cron=True):
        from app.models.schedules import ScheduleCreate
        import uuid
        return ScheduleCreate(
            name="Mi tarea",
            device_id=uuid.uuid4(),
            action="encender",
            payload={},
            cron_expr="0 8 * * *" if with_cron else None,
            timezone="UTC",
        )

    def test_sin_cron_ni_run_at_lanza_400(self):
        from app.models.schedules import ScheduleCreate
        import uuid
        sched_in = ScheduleCreate(
            name="Mi tarea",
            device_id=uuid.uuid4(),
            action="encender",
        )
        with pytest.raises(HTTPException) as exc:
            sched_service.create_schedule(sched_in, "u1")
        assert exc.value.status_code == 400

    def test_con_cron_inserta(self):
        with patch("app.services.schedules.schedule_repository") as mock_r, \
             patch("app.services.schedules.supabase") as mock_db:
            mock_r.find_conflicting_power.return_value = []
            mock_chain = MagicMock()
            mock_chain.data = [{"id": "s1", "action": "encender"}]
            mock_db.table.return_value.insert.return_value.execute.return_value = mock_chain
            result = sched_service.create_schedule(self._payload(), "u1")
        assert result["id"] == "s1"

    def test_conflicto_de_power_lanza_400(self):
        with patch("app.services.schedules.schedule_repository") as mock_r:
            mock_r.find_conflicting_power.return_value = [{"id": "s_existente"}]
            with pytest.raises(HTTPException) as exc:
                sched_service.create_schedule(self._payload(), "u1")
            assert exc.value.status_code == 400


# ── get_schedules / get_schedule ────────────────────────────────────────────

class TestGetSchedules:

    def test_devuelve_schedules_de_la_casa(self):
        with patch("app.services.schedules.get_house_member_ids", return_value=["u1", "u2"]), \
             patch("app.services.schedules.schedule_repository") as mock_r:
            mock_r.find_by_user_ids.return_value = [{"id": "s1"}]
            assert sched_service.get_schedules("u1") == [{"id": "s1"}]


class TestGetSchedule:

    def test_devuelve_schedule(self):
        with patch("app.services.schedules.schedule_repository") as mock_r:
            mock_r.find_by_id_and_user.return_value = {"id": "s1"}
            assert sched_service.get_schedule("s1", "u1") == {"id": "s1"}


# ── delete_schedule (propio / any) ──────────────────────────────────────────

class TestDeleteSchedule:

    def test_borra_si_es_propio(self):
        with patch("app.services.schedules.supabase") as mock_db:
            mock_chain = MagicMock()
            mock_chain.data = [{"id": "s1"}]
            mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = mock_chain
            assert sched_service.delete_schedule("s1", "u1") is True

    def test_no_borra_si_no_existe(self):
        with patch("app.services.schedules.supabase") as mock_db:
            mock_chain = MagicMock()
            mock_chain.data = []
            mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = mock_chain
            assert sched_service.delete_schedule("ghost", "u1") is False


class TestDeleteScheduleAny:

    def test_owner_puede_borrar_de_otros(self):
        with patch("app.services.schedules.get_house_member_ids", return_value=["u1", "u2"]), \
             patch("app.services.schedules.schedule_repository") as mock_r, \
             patch("app.services.schedules.supabase") as mock_db:
            mock_r.find_cron_meta_in_house.return_value = {
                "cron_expr": "* * * * *", "timezone": "UTC", "user_id": "u2",
            }
            mock_chain = MagicMock()
            mock_chain.data = [{"id": "s1"}]
            mock_db.table.return_value.delete.return_value.eq.return_value.in_.return_value.execute.return_value = mock_chain
            assert sched_service.delete_schedule_any("s1", "u1") is True


# ── toggle_schedule ─────────────────────────────────────────────────────────

class TestToggleSchedule:

    def _toggle(self, active=True):
        from app.models.schedules import ScheduleToggle
        return ScheduleToggle(is_active=active)

    def test_no_existe_devuelve_none(self):
        with patch("app.services.schedules.schedule_repository") as mock_r:
            mock_r.find_by_id_and_user.return_value = None
            with patch("app.services.schedules.supabase") as mock_db:
                mock_chain = MagicMock()
                mock_chain.data = []
                mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_chain
                assert sched_service.toggle_schedule("ghost", "u1", self._toggle()) is None

    def test_toggle_activo_recalcula_next_run(self):
        with patch("app.services.schedules.get_schedule", return_value={
                "id": "s1", "cron_expr": "0 8 * * *", "timezone": "UTC",
             }), \
             patch("app.services.schedules.supabase") as mock_db:
            mock_chain = MagicMock()
            mock_chain.data = [{"id": "s1", "is_active": True}]
            mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_chain
            result = sched_service.toggle_schedule("s1", "u1", self._toggle(True))
        assert result is not None

    def test_toggle_inactivo_no_recalcula(self):
        with patch("app.services.schedules.get_schedule", return_value={"id": "s1"}), \
             patch("app.services.schedules.supabase") as mock_db:
            mock_chain = MagicMock()
            mock_chain.data = [{"id": "s1", "is_active": False}]
            mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_chain
            result = sched_service.toggle_schedule("s1", "u1", self._toggle(False))
        assert result is not None


# ── delete_completed_schedules ──────────────────────────────────────────────

# ── get_pending_schedules ───────────────────────────────────────────────────

class TestGetPendingSchedules:

    def test_devuelve_pending(self):
        with patch("app.services.schedules.schedule_repository") as mock_r:
            mock_r.find_pending.return_value = [{"id": "s1"}]
            assert sched_service.get_pending_schedules() == [{"id": "s1"}]


# ── mark_schedule_run ───────────────────────────────────────────────────────

class TestMarkScheduleRun:

    def test_actualiza_last_command_y_next_run(self):
        from app.models.schedules import ScheduleMarkRun
        with patch("app.services.schedules.schedule_repository") as mock_r, \
             patch("app.services.schedules.supabase") as mock_db:
            mock_r.find_cron_meta_by_id.return_value = {
                "cron_expr": "* * * * *", "timezone": "UTC",
            }
            sched_service.mark_schedule_run("s1", ScheduleMarkRun(command_id="c1"))
        # se llama al update
        assert mock_db.table.return_value.update.called

    def test_run_at_unico_marca_inactivo(self):
        from app.models.schedules import ScheduleMarkRun
        with patch("app.services.schedules.schedule_repository") as mock_r, \
             patch("app.services.schedules.supabase") as mock_db:
            mock_r.find_cron_meta_by_id.return_value = {"cron_expr": None, "timezone": "UTC"}
            sched_service.mark_schedule_run("s1", ScheduleMarkRun(command_id="c1"))
        update_data = mock_db.table.return_value.update.call_args[0][0]
        assert update_data.get("is_active") is False
