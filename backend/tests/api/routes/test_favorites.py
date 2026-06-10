import uuid

from fastapi.testclient import TestClient

from tests.conftest import SupabaseMock, make_favorite


class TestListFavorites:

    def test_returns_user_favorites_or_empty(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("favorite_actions", [
            make_favorite(position=0, label="Encender salón"),
            make_favorite(position=1, label="Apagar dormitorio"),
        ])
        assert len(client.get("/api/v1/favorite-actions/").json()) == 2

        supabase_mock.set_data("favorite_actions", [])
        assert client.get("/api/v1/favorite-actions/").json() == []


class TestAddFavorite:

    def test_creates_favorite_when_under_limit(self, client: TestClient, supabase_mock: SupabaseMock):
        device_id = str(uuid.uuid4())
        new_fav = make_favorite(device_id=device_id, action="encender", label="Luz salón")
        supabase_mock.set_data("favorite_actions", [new_fav])

        res = client.post("/api/v1/favorite-actions/", json={
            "device_id": device_id, "action": "encender",
            "payload": {}, "label": "Luz salón",
        })
        assert res.status_code == 201 and res.json()["label"] == "Luz salón"

    def test_rejects_seventh_favorite(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("favorite_actions", [make_favorite() for _ in range(6)])
        res = client.post("/api/v1/favorite-actions/", json={
            "device_id": str(uuid.uuid4()), "action": "encender",
            "payload": {}, "label": "Séptimo",
        })
        assert res.status_code == 400 and "6" in res.json()["detail"]


class TestDeleteFavorite:

    def test_delete_returns_204_or_404(self, client: TestClient, supabase_mock: SupabaseMock):
        fav = make_favorite()
        supabase_mock.set_data("favorite_actions", [fav])
        assert client.delete(f"/api/v1/favorite-actions/{fav['id']}").status_code == 204

        supabase_mock.set_data("favorite_actions", [])
        res = client.delete("/api/v1/favorite-actions/nonexistent-id")
        assert res.status_code == 404 and "no encontrado" in res.json()["detail"].lower()
