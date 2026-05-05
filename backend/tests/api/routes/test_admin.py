"""Tests para las rutas de administración (/admin). Solo accesibles por superusuarios."""
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from tests.conftest import SupabaseMock, TEST_USER_ID


def make_device(**kwargs) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "owner_id": TEST_USER_ID,
        "name": "Luz salón",
        "type": "Luz",
        "driver": "tuya",
        "ip": "192.168.1.100",
        "mac": "AA:BB:CC:DD:EE:FF",
        "is_online": True,
        "room_id": None,
        "registered_at": "2026-04-19T10:00:00+00:00",
        **kwargs,
    }


def make_command(**kwargs) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": TEST_USER_ID,
        "device_id": str(uuid.uuid4()),
        "action": "encender",
        "payload": {},
        "status": "executed",
        "source_type": "direct",
        "source_id": None,
        "executed_at": "2026-04-19T10:01:00+00:00",
        "error": None,
        "created_at": "2026-04-19T10:00:00+00:00",
        **kwargs,
    }


def make_schedule(**kwargs) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": TEST_USER_ID,
        "device_id": str(uuid.uuid4()),
        "name": "Apagar luces",
        "action": "apagar",
        "payload": {},
        "cron_expr": "0 22 * * *",
        "next_run_at": "2026-04-20T22:00:00+00:00",
        "is_active": True,
        "last_command_id": None,
        "created_at": "2026-04-19T10:00:00+00:00",
        **kwargs,
    }


# ── Fixture: superuser client ─────────────────────────────────────────────────

@pytest.fixture()
def admin_client(client: TestClient):
    """Reutiliza el client de sesión cambiando el usuario a superusuario."""
    from app.main import app
    from app.api.deps import get_current_user, get_current_active_superuser

    superuser = {
        "id": TEST_USER_ID,
        "email": "admin@example.com",
        "username": "admin",
        "is_active": True,
        "is_superuser": True,
    }
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: superuser
    app.dependency_overrides[get_current_active_superuser] = lambda: superuser

    yield client

    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


# ── Stats ─────────────────────────────────────────────────────────────────────

class TestAdminStats:
    def test_returns_stats(self, admin_client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("base_user", [{"id": TEST_USER_ID}])
        supabase_mock.set_data("devices", [
            {"id": str(uuid.uuid4()), "is_online": True},
            {"id": str(uuid.uuid4()), "is_online": False},
        ])
        supabase_mock.set_data("schedules", [{"id": str(uuid.uuid4()), "is_active": True}])
        supabase_mock.set_data("commands", [{"id": str(uuid.uuid4())}])

        res = admin_client.get("/api/v1/admin/stats")

        assert res.status_code == 200
        data = res.json()
        assert "users" in data
        assert "devices" in data
        assert "devices_online" in data
        assert "devices_offline" in data
        assert "schedules" in data
        assert "schedules_active" in data
        assert "commands" in data

    def test_requires_superuser(self, client: TestClient):
        res = client.get("/api/v1/admin/stats")
        assert res.status_code == 403


# ── Devices ───────────────────────────────────────────────────────────────────

class TestAdminDevices:
    def test_returns_device_list(self, admin_client: TestClient, supabase_mock: SupabaseMock):
        d = make_device()
        supabase_mock.set_data("devices", [d])
        supabase_mock.set_data("base_user", [])
        supabase_mock.set_data("rooms", [])

        res = admin_client.get("/api/v1/admin/devices")

        assert res.status_code == 200
        data = res.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_returns_empty_when_no_devices(self, admin_client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("devices", [])

        res = admin_client.get("/api/v1/admin/devices")

        assert res.status_code == 200
        assert res.json() == {"data": [], "count": 0}

    def test_requires_superuser(self, client: TestClient):
        res = client.get("/api/v1/admin/devices")
        assert res.status_code == 403


# ── Commands ──────────────────────────────────────────────────────────────────

class TestAdminCommands:
    def test_returns_command_list(self, admin_client: TestClient, supabase_mock: SupabaseMock):
        cmd = make_command()
        supabase_mock.set_data("commands", [cmd])
        supabase_mock.set_data("base_user", [])
        supabase_mock.set_data("devices", [])

        res = admin_client.get("/api/v1/admin/commands")

        assert res.status_code == 200
        data = res.json()
        assert "data" in data
        assert len(data["data"]) == 1

    def test_returns_empty_when_no_commands(self, admin_client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("commands", [])

        res = admin_client.get("/api/v1/admin/commands")

        assert res.status_code == 200
        assert res.json() == {"data": [], "count": 0}

    def test_requires_superuser(self, client: TestClient):
        res = client.get("/api/v1/admin/commands")
        assert res.status_code == 403


# ── Schedules ─────────────────────────────────────────────────────────────────

class TestAdminSchedules:
    def test_returns_schedule_list(self, admin_client: TestClient, supabase_mock: SupabaseMock):
        s = make_schedule()
        supabase_mock.set_data("schedules", [s])
        supabase_mock.set_data("base_user", [])
        supabase_mock.set_data("devices", [])

        res = admin_client.get("/api/v1/admin/schedules")

        assert res.status_code == 200
        data = res.json()
        assert "data" in data
        assert len(data["data"]) == 1

    def test_returns_empty_when_no_schedules(self, admin_client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("schedules", [])

        res = admin_client.get("/api/v1/admin/schedules")

        assert res.status_code == 200
        assert res.json() == {"data": [], "count": 0}

    def test_requires_superuser(self, client: TestClient):
        res = client.get("/api/v1/admin/schedules")
        assert res.status_code == 403
