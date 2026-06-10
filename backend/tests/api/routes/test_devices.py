from unittest.mock import MagicMock, patch

import pytest
import requests as req
from fastapi.testclient import TestClient

from tests.conftest import (
    SupabaseMock, TEST_MEMBER_ID, TEST_USER_ID,
    make_device, make_house, make_house_member,
)


def _setup_house(supabase_mock: SupabaseMock):
    supabase_mock.set_data("houses", [make_house()])
    supabase_mock.set_data("house_members", [make_house_member()])


class TestGetDevices:

    def test_returns_house_devices(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("devices", [
            make_device(name="Luz salón"),
            make_device(name="TV", type="SmartTV", owner_id=TEST_MEMBER_ID),
        ])
        res = client.get("/api/v1/devices/")
        assert res.status_code == 200 and len(res.json()) == 2

class TestGetDevice:

    def test_returns_single_device_or_404(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        device = make_device()
        supabase_mock.set_data("devices", [device])
        assert client.get(f"/api/v1/devices/{device['id']}").json()["id"] == device["id"]

        supabase_mock.set_data("devices", [])
        assert client.get("/api/v1/devices/nonexistent-id").status_code == 404


class TestVincularDevice:

    def test_vincular_success(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("devices", [make_device()])
        res = client.post("/api/v1/devices/vincular", json={
            "ip": "192.168.1.101", "mac": "AA:BB:CC:DD:EE:01",
            "hostname": "luz-cocina", "tipo": "Luz", "name": "Luz cocina",
        })
        assert res.status_code == 200

class TestDesvincularDevice:

    def test_desvincular_returns_ok_or_404(self, client: TestClient, supabase_mock: SupabaseMock):
        device = make_device()
        supabase_mock.set_data("devices", [device])
        assert client.delete(f"/api/v1/devices/{device['id']}").json() == {"ok": True}

        supabase_mock.set_data("devices", [])
        assert client.delete("/api/v1/devices/nonexistent-id").status_code == 404


class TestGetAllDevices:

    def test_returns_house_devices_filtered_by_user(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("devices", [
            make_device(owner_id=TEST_USER_ID),
            make_device(owner_id=TEST_MEMBER_ID, mac="BB:BB:BB:BB:BB:BB"),
        ])
        res = client.get(f"/api/v1/devices/all?user_id={TEST_USER_ID}")
        assert res.status_code == 200 and len(res.json()) == 2

class TestUpdateAndGetStatus:

    def test_update_status_returns_ok_or_404(self, client: TestClient, supabase_mock: SupabaseMock):
        device = make_device()
        supabase_mock.set_data("devices", [device])
        res = client.patch(f"/api/v1/devices/{device['id']}/status",
                           json={"is_online": True, "estado": {"power": "on"}})
        assert res.json() == {"ok": True}

        supabase_mock.set_data("devices", [])
        assert client.patch("/api/v1/devices/nonexistent/status",
                            json={"is_online": False, "estado": {}}).status_code == 404

    def test_get_status_returns_state(self, client: TestClient, supabase_mock: SupabaseMock):
        device = make_device(estado={"power": "on"})
        supabase_mock.set_data("devices", [device])
        data = client.get(f"/api/v1/devices/{device['id']}/status").json()
        assert data["is_online"] is True and "estado" in data


class TestHaConnection:

    def test_get_connection_when_not_connected(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("ha_integrations", [])
        res = client.get("/api/v1/devices/ha/connection")
        assert res.status_code == 200 and res.json()["connected"] is False

    def test_delete_connection_returns_ok(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("ha_integrations", [{"user_id": TEST_USER_ID}])
        supabase_mock.set_data("devices", [])
        assert client.delete("/api/v1/devices/ha/connection").json() == {"ok": True}

    def test_connect_with_unreachable_server_returns_400(self, client: TestClient):
        with patch("app.services.devices.requests.get", side_effect=req.ConnectionError):
            res = client.post("/api/v1/devices/ha/connect",
                              json={"ha_url": "http://invalid-host:8123", "token": "fake-token"})
        assert res.status_code == 400

    def test_connect_imports_supported_entities(self, client: TestClient, supabase_mock: SupabaseMock):
        _setup_house(supabase_mock)
        supabase_mock.set_data("ha_integrations", [])
        supabase_mock.set_data("devices", [make_device()])

        api = MagicMock(); api.raise_for_status = lambda: None
        states = MagicMock(); states.raise_for_status = lambda: None
        states.json.return_value = [
            {"entity_id": "light.salon",  "state": "on",  "attributes": {"friendly_name": "Luz salón"}},
            {"entity_id": "switch.cocina","state": "off", "attributes": {"friendly_name": "Enchufe cocina"}},
            {"entity_id": "sensor.temp",  "state": "22",  "attributes": {}},
        ]
        with patch("app.services.devices.requests.get", side_effect=[api, states]):
            res = client.post("/api/v1/devices/ha/connect",
                              json={"ha_url": "http://192.168.1.50:8123", "token": "valid-token"})
        assert res.status_code == 200 and res.json()["importados"] == 2
