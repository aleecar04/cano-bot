"""Tests para las rutas de administración (/admin). Solo accesibles por superusuarios."""
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import SupabaseMock, TEST_USER_ID


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
        supabase_mock.set_data("houses", [{"id": str(uuid.uuid4())}])
        supabase_mock.set_data("devices", [
            {"id": str(uuid.uuid4()), "is_online": True},
            {"id": str(uuid.uuid4()), "is_online": False},
        ])

        res = admin_client.get("/api/v1/admin/stats")

        assert res.status_code == 200
        data = res.json()
        assert "users" in data
        assert "houses" in data
        assert "devices" in data
        assert "devices_online" in data
        assert "devices_offline" in data

    def test_requires_superuser(self, client: TestClient):
        res = client.get("/api/v1/admin/stats")
        assert res.status_code == 403


# ── Houses ────────────────────────────────────────────────────────────────────

class TestAdminHouses:
    def test_returns_house_list(self, admin_client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [{"id": str(uuid.uuid4()), "name": "Casa Demo"}])
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("devices", [])

        res = admin_client.get("/api/v1/admin/houses")

        assert res.status_code == 200
        data = res.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_requires_superuser(self, client: TestClient):
        res = client.get("/api/v1/admin/houses")
        assert res.status_code == 403
