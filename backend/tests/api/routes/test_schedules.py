"""Tests para las rutas de tareas programadas (/schedules)."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from tests.conftest import SupabaseMock, make_schedule, make_house, TEST_MEMBER_ID, TEST_USER_ID

_NO_CONFLICT = patch("app.services.schedules._check_conflicting_power_schedule")

from tests.conftest import TEST_HOUSE_ID, make_house, make_house_member

_HOUSE_MEMBERS = [
    make_house_member(TEST_HOUSE_ID, TEST_USER_ID, "owner"),
    make_house_member(TEST_HOUSE_ID, TEST_MEMBER_ID, "member"),
]


class TestListSchedules:
    def test_returns_house_schedules(self, client: TestClient, supabase_mock: SupabaseMock):
        """Schedules from all house members are visible."""
        s1 = make_schedule(name="Apagar luces", user_id=TEST_USER_ID)
        s2 = make_schedule(name="Encender calefacción", user_id=TEST_MEMBER_ID)
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", _HOUSE_MEMBERS)
        supabase_mock.set_data("schedules", [s1, s2])


        res = client.get("/api/v1/schedules/")

        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_returns_empty_list(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", _HOUSE_MEMBERS)
        supabase_mock.set_data("schedules", [])


        res = client.get("/api/v1/schedules/")

        assert res.status_code == 200
        assert res.json() == []


class TestPowerActionConflict:
    def test_rejects_conflicting_power_action(self, client: TestClient, supabase_mock: SupabaseMock):
        """Cannot schedule encender+apagar on same device at the same minute."""
        import uuid
        device_id = str(uuid.uuid4())
        existing = make_schedule(
            device_id=device_id,
            action="encender",
            next_run_at="2026-06-01T09:00:00+00:00",
        )
        # Mock: schedules table returns an existing power schedule for conflict check
        supabase_mock.set_data("schedules", [existing])
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", _HOUSE_MEMBERS)

        payload = {
            "device_id": device_id,
            "name": "Apagar a las 9",
            "action": "apagar",
            "run_at": "2026-06-01T09:00:30+00:00",  # same minute
        }

        res = client.post("/api/v1/schedules/", json=payload)

        assert res.status_code == 400
        assert "encendido" in res.json()["detail"].lower() or "apagado" in res.json()["detail"].lower()

    def test_allows_non_power_action_at_same_time(self, client: TestClient, supabase_mock: SupabaseMock):
        """brillo at same minute as encender is allowed."""
        import uuid
        device_id = str(uuid.uuid4())
        new_schedule = make_schedule(device_id=device_id, action="brillo")
        # power schedule exists but action is brillo — no conflict
        existing_power = make_schedule(
            device_id=device_id,
            action="encender",
            next_run_at="2026-06-01T09:00:00+00:00",
        )
        supabase_mock.set_data("schedules", [new_schedule])
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", _HOUSE_MEMBERS)

        payload = {
            "device_id": device_id,
            "name": "Brillo al 70%",
            "action": "brillo",
            "payload": {"valor": 70},
            "run_at": "2026-06-01T09:00:00+00:00",
        }

        res = client.post("/api/v1/schedules/", json=payload)

        assert res.status_code == 201


class TestCreateSchedule:
    def test_creates_recurring_schedule(self, client: TestClient, supabase_mock: SupabaseMock):
        new_schedule = make_schedule(name="Test")
        supabase_mock.set_data("schedules", [new_schedule])

        payload = {
            "device_id": new_schedule["device_id"],
            "name": "Test",
            "action": "apagar",
            "payload": {},
            "cron_expr": "0 22 * * *",
        }

        with _NO_CONFLICT:
            res = client.post("/api/v1/schedules/", json=payload)

        assert res.status_code == 201
        assert res.json()["cron_expr"] == "0 22 * * *"

    def test_creates_onetime_schedule(self, client: TestClient, supabase_mock: SupabaseMock):
        new_schedule = make_schedule(cron_expr=None, next_run_at="2026-05-01T08:00:00+00:00")
        supabase_mock.set_data("schedules", [new_schedule])

        payload = {
            "device_id": new_schedule["device_id"],
            "name": "Encender una vez",
            "action": "encender",
            "payload": {},
            "run_at": "2026-05-01T08:00:00+00:00",
        }

        with _NO_CONFLICT:
            res = client.post("/api/v1/schedules/", json=payload)

        assert res.status_code == 201
        assert res.json()["cron_expr"] is None

    def test_without_cron_or_run_at_returns_400(self, client: TestClient, supabase_mock: SupabaseMock):
        """Neither cron_expr nor run_at provided — backend should return 400."""
        payload = {
            "device_id": str(__import__("uuid").uuid4()),
            "name": "Bad schedule",
            "action": "apagar",
            "payload": {},
        }

        res = client.post("/api/v1/schedules/", json=payload)

        assert res.status_code == 400


class TestOwnerDeleteOthersSchedule:
    def test_owner_can_delete_any_schedule(self, client: TestClient, supabase_mock: SupabaseMock):
        """Owner can delete schedules created by other house members."""
        schedule = make_schedule(user_id=TEST_MEMBER_ID)
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", _HOUSE_MEMBERS)
        supabase_mock.set_data("schedules", [schedule])

        res = client.delete(f"/api/v1/schedules/{schedule['id']}")

        assert res.status_code == 204


class TestDeleteSchedule:
    def test_deletes_existing_schedule(self, client: TestClient, supabase_mock: SupabaseMock):
        schedule = make_schedule()
        supabase_mock.set_data("schedules", [schedule])

        res = client.delete(f"/api/v1/schedules/{schedule['id']}")

        assert res.status_code == 204

    def test_returns_404_when_not_found(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("schedules", [])

        res = client.delete("/api/v1/schedules/nonexistent-id")

        assert res.status_code == 404


class TestToggleSchedule:
    def test_disables_active_schedule(self, client: TestClient, supabase_mock: SupabaseMock):
        schedule = make_schedule(is_active=True)
        supabase_mock.set_data("schedules", [schedule])

        res = client.patch(
            f"/api/v1/schedules/{schedule['id']}/toggle",
            json={"is_active": False},
        )

        assert res.status_code == 200
        # El mock devuelve el schedule original; verificamos que la ruta responde bien
        assert res.json()["id"] == schedule["id"]

    def test_returns_404_when_not_found(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("schedules", [])

        res = client.patch(
            "/api/v1/schedules/nonexistent/toggle",
            json={"is_active": True},
        )

        assert res.status_code == 404


