from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from supabase import Client

from tests.conftest import (
    TEST_MEMBER_ID, TEST_USER_ID,
    make_device, make_house, make_house_member,
)


def _setup_house(supabase: Client):
    supabase.table("houses").insert(make_house()).execute()
    supabase.table("house_members").insert(make_house_member()).execute()


class TestDevicesRoutes:

    def test_returns_house_devices(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        supabase.table("devices").insert([
            make_device(name="Lampara Salon"),
            make_device(name="TV", type="SmartTV", owner_id=TEST_MEMBER_ID),
        ]).execute()
        res = client.get("/api/v1/devices/")
        assert res.status_code == 200 and len(res.json()) == 2

    def test_returns_single_device_or_404(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        device = make_device()
        supabase.table("devices").insert(device).execute()
        assert client.get(f"/api/v1/devices/{device['id']}").json()["id"] == device["id"]

        assert client.get("/api/v1/devices/00000000-0000-0000-0000-000000000099").status_code == 404

    def test_refresh_returns_404_when_device_not_found(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        assert client.post("/api/v1/devices/00000000-0000-0000-0000-000000000099/refresh").status_code == 404

    def test_refresh_triggers_poll_and_returns_202(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        device = make_device()
        supabase.table("devices").insert(device).execute()
        with patch("app.api.routes.devices.device_service.request_device_poll", new_callable=AsyncMock) as mock_poll:
            res = client.post(f"/api/v1/devices/{device['id']}/refresh")
        assert res.status_code == 202
        assert res.json() == {"ok": True}
        mock_poll.assert_awaited_once()

    def test_vincular_success(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        res = client.post("/api/v1/devices/vincular", json={
            "ip": "192.0.2.101", "mac": "AA:BB:CC:DD:EE:01",
            "hostname": "luz-cocina", "tipo": "Luz", "name": "Lampara Salon",
        })
        assert res.status_code == 200

    def test_desvincular_returns_ok(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        device = make_device()
        supabase.table("devices").insert(device).execute()
        assert client.delete(f"/api/v1/devices/{device['id']}").json() == {"ok": True}

    def test_get_all_devices_filtered_by_user(self, client: TestClient, supabase: Client):
        supabase.table("houses").insert(make_house()).execute()
        supabase.table("devices").insert([
            make_device(owner_id=TEST_USER_ID),
            make_device(owner_id=TEST_MEMBER_ID, mac="BB:BB:BB:BB:BB:BB"),
        ]).execute()
        res = client.get(f"/api/v1/devices/all?user_id={TEST_USER_ID}")
        assert res.status_code == 200 and len(res.json()) == 2

    def test_update_status_returns_ok(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        device = make_device()
        supabase.table("devices").insert(device).execute()
        res = client.patch(f"/api/v1/devices/{device['id']}/status",
                           json={"is_online": True, "state": {"power": "on"}})
        assert res.json() == {"ok": True}

    def test_get_status_returns_state(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        device = make_device(state={"power": "on"})
        supabase.table("devices").insert(device).execute()
        data = client.get(f"/api/v1/devices/{device['id']}/status").json()
        assert data["is_online"] is True and "state" in data

    def test_delete_ha_connection_returns_ok(self, client: TestClient, supabase: Client):
        _setup_house(supabase)
        supabase.table("ha_integrations").insert({
            "house_id": make_house()["id"],
            "ha_url": "http://192.0.2.50:8123",
            "token": "valid-token",
        }).execute()
        assert client.delete("/api/v1/devices/ha/connection").json() == {"ok": True}

    def test_connect_ha_imports_supported_entities(self, client: TestClient, supabase: Client):
        _setup_house(supabase)

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
