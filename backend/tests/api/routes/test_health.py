from fastapi.testclient import TestClient


class TestHealthRoutes:

    def test_health_check_returns_ok(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}
