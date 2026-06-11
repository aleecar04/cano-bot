import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tests.conftest import SupabaseMock, make_favorite


class TestFavoritesRoutes:

    def test_creates_favorite_when_under_limit(self, client: TestClient, supabase_mock: SupabaseMock):
        device_id = str(uuid.uuid4())
        new_fav = make_favorite(device_id=device_id, action="encender", label="Lampara Salon")
        supabase_mock.set_data("favorite_actions", [new_fav])

        res = client.post("/api/v1/favorite-actions/", json={
            "device_id": device_id, "action": "encender",
            "payload": {}, "label": "Lampara Salon",
        })
        assert res.status_code == 201 and res.json()["label"] == "Lampara Salon"

    def test_rejects_seventh_favorite(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("favorite_actions", [make_favorite() for _ in range(6)])
        res = client.post("/api/v1/favorite-actions/", json={
            "device_id": str(uuid.uuid4()), "action": "encender",
            "payload": {}, "label": "Séptimo",
        })
        assert res.status_code == 400 and "6" in res.json()["detail"]

    def test_delete_returns_204(self, client: TestClient, supabase_mock: SupabaseMock):
        fav = make_favorite()
        supabase_mock.set_data("favorite_actions", [fav])
        assert client.delete(f"/api/v1/favorite-actions/{fav['id']}").status_code == 204

    def test_update_returns_404_when_missing(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("favorite_actions", [])
        res = client.patch("/api/v1/favorite-actions/missing-id", json={
            "action": "encender", "payload": {}, "label": "x",
        })
        assert res.status_code == 404

    def test_update_returns_updated_row(self, client: TestClient, supabase_mock: SupabaseMock):
        fav = make_favorite(label="old")
        supabase_mock.set_data("favorite_actions", [fav])
        res = client.patch(f"/api/v1/favorite-actions/{fav['id']}", json={
            "action": "apagar", "payload": {}, "label": "nuevo",
        })
        assert res.status_code == 200

    def test_executes_known_favorite(self, client: TestClient, supabase_mock: SupabaseMock):
        fav = make_favorite()
        supabase_mock.set_data("favorite_actions", [fav])
        with patch("app.services.favorites.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"ok": True, "command_id": "cmd_nuevo"}
            res = client.post(f"/api/v1/favorite-actions/{fav['id']}/execute")
        assert res.status_code == 200

    def test_returns_404_for_unknown_favorite(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("favorite_actions", [])
        res = client.post("/api/v1/favorite-actions/missing-id/execute")
        assert res.status_code == 404
