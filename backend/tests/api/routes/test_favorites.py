"""Tests para las rutas de acciones favoritas (/favorite-actions)."""
import pytest
from fastapi.testclient import TestClient

from tests.conftest import SupabaseMock, make_favorite


class TestListFavorites:
    def test_returns_user_favorites(self, client: TestClient, supabase_mock: SupabaseMock):
        fav1 = make_favorite(position=0, label="Encender salón")
        fav2 = make_favorite(position=1, label="Apagar dormitorio")
        supabase_mock.set_data("favorite_actions", [fav1, fav2])

        res = client.get("/api/v1/favorite-actions/")

        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["label"] == "Encender salón"
        assert data[1]["label"] == "Apagar dormitorio"

    def test_returns_empty_list(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("favorite_actions", [])

        res = client.get("/api/v1/favorite-actions/")

        assert res.status_code == 200
        assert res.json() == []


class TestAddFavorite:
    def test_creates_favorite_successfully(self, client: TestClient, supabase_mock: SupabaseMock):
        # Sin favoritos previos
        supabase_mock.set_data("favorite_actions", [])

        import uuid
        device_id = str(uuid.uuid4())
        new_fav = make_favorite(device_id=device_id, action="encender", label="Luz salón")
        # Después del insert, supabase devuelve el nuevo favorito
        supabase_mock.set_data("favorite_actions", [new_fav])

        payload = {
            "device_id": device_id,
            "action": "encender",
            "payload": {},
            "label": "Luz salón",
        }

        res = client.post("/api/v1/favorite-actions/", json=payload)

        assert res.status_code == 201
        data = res.json()
        assert data["action"] == "encender"
        assert data["label"] == "Luz salón"

    def test_rejects_fifth_favorite(self, client: TestClient, supabase_mock: SupabaseMock):
        """No se pueden tener más de 4 favoritos."""
        existing = [make_favorite(position=i) for i in range(4)]
        supabase_mock.set_data("favorite_actions", existing)

        import uuid
        payload = {
            "device_id": str(uuid.uuid4()),
            "action": "encender",
            "payload": {},
            "label": "Quinto favorito",
        }

        res = client.post("/api/v1/favorite-actions/", json=payload)

        assert res.status_code == 400
        assert "4" in res.json()["detail"]

    def test_creates_up_to_four_favorites(self, client: TestClient, supabase_mock: SupabaseMock):
        """Con 3 favoritos existentes se puede añadir el 4to (límite es 4)."""
        import uuid
        existing = [make_favorite(position=i) for i in range(3)]
        device_id = str(uuid.uuid4())
        fourth_fav = make_favorite(position=3, device_id=device_id)

        # El mock devuelve los mismos datos para select e insert.
        # El servicio llama get_favorites() y verifica len < 4.
        # Ponemos 3 items para que la validación pase, y el insert retorna el 4to.
        supabase_mock.set_data("favorite_actions", [*existing, fourth_fav])

        # Sobreescribimos set_data con un mock que devuelve 3 en select
        # y el 4to en insert. Para simplificar, verificamos que con < 4 pasa:
        supabase_mock.set_data("favorite_actions", existing)

        payload = {
            "device_id": device_id,
            "action": "apagar",
            "payload": {},
            "label": "Cuarto favorito",
        }

        res = client.post("/api/v1/favorite-actions/", json=payload)

        # 3 existentes → 4to es válido (el insert devolverá el primer item del mock como placeholder)
        assert res.status_code == 201


class TestDeleteFavorite:
    def test_deletes_existing_favorite(self, client: TestClient, supabase_mock: SupabaseMock):
        fav = make_favorite()
        supabase_mock.set_data("favorite_actions", [fav])

        res = client.delete(f"/api/v1/favorite-actions/{fav['id']}")

        assert res.status_code == 204

    def test_returns_404_when_not_found(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("favorite_actions", [])

        res = client.delete("/api/v1/favorite-actions/nonexistent-id")

        assert res.status_code == 404
        assert "no encontrado" in res.json()["detail"].lower()
