import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from supabase import Client

from tests.conftest import (
    TEST_HOUSE_ID, TEST_MEMBER_ID, TEST_USER_ID,
    make_device, make_house, make_house_member, make_schedule,
)

_NO_CONFLICT = patch("app.services.schedules._check_conflicting_power_schedule")


def _setup_house_with_device(supabase: Client):
    supabase.table("houses").insert(make_house()).execute()
    supabase.table("house_members").insert([
        make_house_member(TEST_HOUSE_ID, TEST_USER_ID, "owner"),
        make_house_member(TEST_HOUSE_ID, TEST_MEMBER_ID, "member"),
    ]).execute()
    device = make_device()
    supabase.table("devices").insert(device).execute()
    return device


class TestSchedulesRoutes:

    def test_returns_house_schedules(self, client: TestClient, supabase: Client):
        device = _setup_house_with_device(supabase)
        supabase.table("schedules").insert([
            make_schedule(device_id=device["id"], name="Apagar", user_id=TEST_USER_ID),
            make_schedule(device_id=device["id"], name="Encender", user_id=TEST_MEMBER_ID),
        ]).execute()
        assert len(client.get("/api/v1/schedules/").json()) == 2

    def test_returns_empty_when_no_schedules(self, client: TestClient, supabase: Client):
        _setup_house_with_device(supabase)
        assert client.get("/api/v1/schedules/").json() == []

    def test_rejects_power_action_in_same_minute(self, client: TestClient, supabase: Client):
        device = _setup_house_with_device(supabase)
        supabase.table("schedules").insert(make_schedule(
            device_id=device["id"], action="encender",
            next_run_at="2026-06-01T09:00:00+00:00",
        )).execute()
        res = client.post("/api/v1/schedules/", json={
            "device_id": device["id"], "name": "Apagar",
            "action": "apagar", "run_at": "2026-06-01T09:00:30+00:00",
        })
        assert res.status_code == 400

    def test_creates_schedule_with_cron(self, client: TestClient, supabase: Client):
        device = _setup_house_with_device(supabase)
        with _NO_CONFLICT:
            res = client.post("/api/v1/schedules/", json={
                "device_id": device["id"], "name": "Test",
                "action": "apagar", "payload": {}, "cron_expr": "0 22 * * *",
            })
        assert res.status_code == 201 and res.json()["cron_expr"] == "0 22 * * *"

    def test_without_cron(self, client: TestClient):
        res = client.post("/api/v1/schedules/", json={
            "device_id": str(uuid.uuid4()), "name": "Bad",
            "action": "apagar", "payload": {},
        })
        assert res.status_code == 400

    def test_delete(self, client: TestClient, supabase: Client):
        device = _setup_house_with_device(supabase)
        schedule = make_schedule(device_id=device["id"])
        supabase.table("schedules").insert(schedule).execute()
        assert client.delete(f"/api/v1/schedules/{schedule['id']}").status_code == 204

    def test_toggle(self, client: TestClient, supabase: Client):
        device = _setup_house_with_device(supabase)
        schedule = make_schedule(device_id=device["id"], is_active=True)
        supabase.table("schedules").insert(schedule).execute()
        res = client.patch(f"/api/v1/schedules/{schedule['id']}/toggle", json={"is_active": False})
        assert res.status_code == 200 and res.json()["id"] == schedule["id"]

    def test_toggle_404_when_missing(self, client: TestClient, supabase: Client):
        _setup_house_with_device(supabase)
        assert client.patch(
            f"/api/v1/schedules/{uuid.uuid4()}/toggle",
            json={"is_active": True},
        ).status_code == 404
