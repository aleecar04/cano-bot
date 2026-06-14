import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from supabase import Client

from tests.conftest import make_device, make_favorite, make_house, make_house_member


def _setup_house_with_device(supabase: Client):
    supabase.table("houses").insert(make_house()).execute()
    supabase.table("house_members").insert(make_house_member()).execute()
    device = make_device()
    supabase.table("devices").insert(device).execute()
    return device


class TestFavoritesRoutes:

    def test_creates_favorite_when_under_limit(self, client: TestClient, supabase: Client):
        device = _setup_house_with_device(supabase)
        res = client.post("/api/v1/favorite-actions/", json={
            "device_id": device["id"], "action": "encender",
            "payload": {}, "label": "Lampara Salon",
        })
        assert res.status_code == 201 and res.json()["label"] == "Lampara Salon"

    def test_rejects_seventh_favorite(self, client: TestClient, supabase: Client):
        device = _setup_house_with_device(supabase)
        favs = [
            make_favorite(device_id=device["id"], action=f"act_{i}")
            for i in range(6)
        ]
        supabase.table("favorite_actions").insert(favs).execute()
        res = client.post("/api/v1/favorite-actions/", json={
            "device_id": device["id"], "action": "encender",
            "payload": {}, "label": "Séptimo",
        })
        assert res.status_code == 400 and "6" in res.json()["detail"]

    def test_delete_returns_204(self, client: TestClient, supabase: Client):
        device = _setup_house_with_device(supabase)
        fav = make_favorite(device_id=device["id"])
        supabase.table("favorite_actions").insert(fav).execute()
        assert client.delete(f"/api/v1/favorite-actions/{fav['id']}").status_code == 204

    def test_update_returns_404_when_missing(self, client: TestClient, supabase: Client):
        res = client.patch(
            f"/api/v1/favorite-actions/{uuid.uuid4()}",
            json={"action": "encender", "payload": {}, "label": "x"},
        )
        assert res.status_code == 404

    def test_update_returns_updated_row(self, client: TestClient, supabase: Client):
        device = _setup_house_with_device(supabase)
        fav = make_favorite(device_id=device["id"], label="old")
        supabase.table("favorite_actions").insert(fav).execute()
        res = client.patch(f"/api/v1/favorite-actions/{fav['id']}", json={
            "action": "apagar", "payload": {}, "label": "nuevo",
        })
        assert res.status_code == 200

    def test_executes_known_favorite(self, client: TestClient, supabase: Client):
        device = _setup_house_with_device(supabase)
        fav = make_favorite(device_id=device["id"])
        supabase.table("favorite_actions").insert(fav).execute()
        with patch("app.services.favorites.execute_command", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"ok": True, "command_id": "cmd_nuevo"}
            res = client.post(f"/api/v1/favorite-actions/{fav['id']}/execute")
        assert res.status_code == 200

    def test_returns_404_for_unknown_favorite(self, client: TestClient, supabase: Client):
        res = client.post(f"/api/v1/favorite-actions/{uuid.uuid4()}/execute")
        assert res.status_code == 404
