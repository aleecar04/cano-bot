import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import SupabaseMock, TEST_USER_ID


@pytest.fixture()
def admin_client(client: TestClient):
    from app.api.deps import get_current_active_superuser, get_current_user
    from app.main import app

    superuser = {
        "id": TEST_USER_ID, "email": "admin@example.com", "username": "admin",
        "is_active": True, "is_superuser": True,
    }
    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: superuser
    app.dependency_overrides[get_current_active_superuser] = lambda: superuser
    yield client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


def test_admin_stats_returns_aggregated_counts(admin_client: TestClient, supabase_mock: SupabaseMock):
    supabase_mock.set_data("base_user", [{"id": TEST_USER_ID}])
    supabase_mock.set_data("houses", [{"id": str(uuid.uuid4())}])
    supabase_mock.set_data("devices", [
        {"id": str(uuid.uuid4()), "is_online": True},
        {"id": str(uuid.uuid4()), "is_online": False},
    ])
    data = admin_client.get("/api/v1/admin/stats").json()
    for key in ("users", "houses", "devices", "devices_online", "devices_offline"):
        assert key in data


def test_admin_houses_returns_list(admin_client: TestClient, supabase_mock: SupabaseMock):
    supabase_mock.set_data("houses", [{"id": str(uuid.uuid4()), "name": "Casa Demo"}])
    supabase_mock.set_data("house_members", [])
    supabase_mock.set_data("devices", [])
    res = admin_client.get("/api/v1/admin/houses")
    assert res.status_code == 200 and isinstance(res.json()["data"], list)


@pytest.mark.parametrize("path", ["/api/v1/admin/stats", "/api/v1/admin/houses"])
def test_admin_routes_require_superuser(client: TestClient, path):
    assert client.get(path).status_code == 403
