import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.conftest import (
    SupabaseMock, TEST_HOUSE_ID, TEST_MEMBER_ID, TEST_USER_ID,
    make_house, make_house_member, make_schedule,
)

_NO_CONFLICT = patch("app.services.schedules._check_conflicting_power_schedule")
_HOUSE_MEMBERS = [
    make_house_member(TEST_HOUSE_ID, TEST_USER_ID, "owner"),
    make_house_member(TEST_HOUSE_ID, TEST_MEMBER_ID, "member"),
]


def _setup_house(supabase_mock: SupabaseMock):
    supabase_mock.set_data("houses", [make_house()])
    supabase_mock.set_data("house_members", _HOUSE_MEMBERS)


class TestListSchedules:

    def test_returns_house_schedules_or_empty(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("schedules", [
            make_schedule(name="Apagar", user_id=TEST_USER_ID),
            make_schedule(name="Encender", user_id=TEST_MEMBER_ID),
        ])
        assert len(client.get("/api/v1/schedules/").json()) == 2

        supabase_mock.set_data("schedules", [])
        assert client.get("/api/v1/schedules/").json() == []


class TestPowerActionConflict:

    def test_rejects_conflicting_power_action_within_same_minute(self, client: TestClient, supabase_mock: SupabaseMock):
        device_id = str(uuid.uuid4())
        _setup_house(supabase_mock)
        supabase_mock.set_data("schedules", [make_schedule(
            device_id=device_id, action="encender",
            next_run_at="2026-06-01T09:00:00+00:00",
        )])
        res = client.post("/api/v1/schedules/", json={
            "device_id": device_id, "name": "Apagar",
            "action": "apagar", "run_at": "2026-06-01T09:00:30+00:00",
        })
        assert res.status_code == 400

    def test_allows_non_power_action_at_same_time(self, client: TestClient, supabase_mock: SupabaseMock):
        device_id = str(uuid.uuid4())
        _setup_house(supabase_mock)
        supabase_mock.set_data("schedules", [make_schedule(device_id=device_id, action="brillo")])
        res = client.post("/api/v1/schedules/", json={
            "device_id": device_id, "name": "Brillo", "action": "brillo",
            "payload": {"valor": 70}, "run_at": "2026-06-01T09:00:00+00:00",
        })
        assert res.status_code == 201


class TestCreateSchedule:

    def test_creates_recurring_schedule_with_cron(self, client: TestClient, supabase_mock: SupabaseMock):
        new_schedule = make_schedule(name="Test")
        supabase_mock.set_data("schedules", [new_schedule])
        with _NO_CONFLICT:
            res = client.post("/api/v1/schedules/", json={
                "device_id": new_schedule["device_id"], "name": "Test",
                "action": "apagar", "payload": {}, "cron_expr": "0 22 * * *",
            })
        assert res.status_code == 201 and res.json()["cron_expr"] == "0 22 * * *"

    def test_without_cron_or_run_at_returns_400(self, client: TestClient):
        res = client.post("/api/v1/schedules/", json={
            "device_id": str(uuid.uuid4()), "name": "Bad",
            "action": "apagar", "payload": {},
        })
        assert res.status_code == 400


class TestDeleteAndToggleSchedule:

    def test_delete_returns_204_or_404(self, client: TestClient, supabase_mock: SupabaseMock):
        schedule = make_schedule()
        supabase_mock.set_data("schedules", [schedule])
        assert client.delete(f"/api/v1/schedules/{schedule['id']}").status_code == 204

        supabase_mock.set_data("schedules", [])
        assert client.delete("/api/v1/schedules/nonexistent-id").status_code == 404

    def test_toggle_returns_200_or_404(self, client: TestClient, supabase_mock: SupabaseMock):
        schedule = make_schedule(is_active=True)
        supabase_mock.set_data("schedules", [schedule])
        res = client.patch(f"/api/v1/schedules/{schedule['id']}/toggle", json={"is_active": False})
        assert res.status_code == 200 and res.json()["id"] == schedule["id"]

        supabase_mock.set_data("schedules", [])
        assert client.patch("/api/v1/schedules/nonexistent/toggle",
                            json={"is_active": True}).status_code == 404
