from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from tests.conftest import (
    SupabaseMock, TEST_MEMBER_ID, TEST_USER_ID,
    make_device, make_house, make_house_member,
)


def _setup_house(supabase_mock: SupabaseMock):
    supabase_mock.set_data("houses", [make_house()])
    supabase_mock.set_data("house_members", [make_house_member()])


class TestDevicesRoutes:

    def test_returns_house_devices(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("devices", [
            make_device(name="Lampara Salon"),
            make_device(name="TV", type="SmartTV", owner_id=TEST_MEMBER_ID),
        ])
        res = client.get("/api/v1/devices/")
        assert res.status_code == 200 and len(res.json()) == 2

    def test_returns_single_device_or_404(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        device = make_device()
        supabase_mock.set_data("devices", [device])
        assert client.get(f"/api/v1/devices/{device['id']}").json()["id"] == device["id"]

        supabase_mock.set_data("devices", [])
        assert client.get("/api/v1/devices/nonexistent-id").status_code == 404

    def test_refresh_returns_404_when_device_not_found(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("devices", [])
        assert client.post("/api/v1/devices/missing-id/refresh").status_code == 404

    def test_refresh_triggers_poll_and_returns_202(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        device = make_device()
        supabase_mock.set_data("devices", [device])
        with patch("app.api.routes.devices.device_service.request_device_poll", new_callable=AsyncMock) as mock_poll:
            res = client.post(f"/api/v1/devices/{device['id']}/refresh")
        assert res.status_code == 202
        assert res.json() == {"ok": True}
        mock_poll.assert_awaited_once()

    def test_vincular_success(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("devices", [make_device()])
        res = client.post("/api/v1/devices/vincular", json={
            "ip": "192.0.2.101", "mac": "AA:BB:CC:DD:EE:01",
            "hostname": "luz-cocina", "tipo": "Luz", "name": "Lampara Salon",
        })
        assert res.status_code == 200

    def test_desvincular_returns_ok(self, client: TestClient, supabase_mock: SupabaseMock):
        device = make_device()
        supabase_mock.set_data("devices", [device])
        assert client.delete(f"/api/v1/devices/{device['id']}").json() == {"ok": True}

    def test_get_all_devices_filtered_by_user(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("devices", [
            make_device(owner_id=TEST_USER_ID),
            make_device(owner_id=TEST_MEMBER_ID, mac="BB:BB:BB:BB:BB:BB"),
        ])
        res = client.get(f"/api/v1/devices/all?user_id={TEST_USER_ID}")
        assert res.status_code == 200 and len(res.json()) == 2

    def test_update_status_returns_ok(self, client: TestClient, supabase_mock: SupabaseMock):
        device = make_device()
        supabase_mock.set_data("devices", [device])
        res = client.patch(f"/api/v1/devices/{device['id']}/status",
                           json={"is_online": True, "state": {"power": "on"}})
        assert res.json() == {"ok": True}

    def test_get_status_returns_state(self, client: TestClient, supabase_mock: SupabaseMock):
        device = make_device(state={"power": "on"})
        supabase_mock.set_data("devices", [device])
        data = client.get(f"/api/v1/devices/{device['id']}/status").json()
        assert data["is_online"] is True and "state" in data

    def test_delete_ha_connection_returns_ok(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("ha_integrations", [{"user_id": TEST_USER_ID}])
        supabase_mock.set_data("devices", [])
        assert client.delete("/api/v1/devices/ha/connection").json() == {"ok": True}

    def test_connect_ha_imports_supported_entities(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("ha_integrations", [])
        supabase_mock.set_data("devices", [make_device()])

        api = MagicMock(); api.raise_for_status = lambda: None
        states = MagicMock(); states.raise_for_status = lambda: None
        states.json.return_value = [
            {"entity_id": "light.salon",  "state": "on",  "attributes": {"friendly_name": "Lampara Salon"}},
            {"entity_id": "switch.cocina","state": "off", "attributes": {"friendly_name": "Enchufe Cocina"}},
            {"entity_id": "sensor.temp",  "state": "22",  "attributes": {}},
        ]
        with patch("app.services.devices.requests.get", side_effect=[api, states]):
            res = client.post("/api/v1/devices/ha/connect",
                              json={"ha_url": "http://192.0.2.50:8123", "token": "valid-token"})
        assert res.status_code == 200 and res.json()["importados"] == 2
