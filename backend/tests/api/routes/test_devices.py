"""Tests para las rutas de dispositivos (/devices)."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    WEBHOOK_SECRET, SupabaseMock, TEST_USER_ID, TEST_HOUSE_ID,
    TEST_MEMBER_ID, make_device, make_house, make_house_member,
)

WEBHOOK_HEADERS = {"x-webhook-token": WEBHOOK_SECRET}


def _setup_house(supabase_mock: SupabaseMock):
    house = make_house()
    supabase_mock.set_data("houses", [house])
    supabase_mock.set_data("house_members", [make_house_member()])


class TestGetDevices:
    def test_returns_house_devices(self, client: TestClient, supabase_mock: SupabaseMock):
        """Devices filtered by house_id, not owner_id."""
        house = make_house()
        d1 = make_device(name="Luz salón")
        d2 = make_device(name="TV dormitorio", type="SmartTV", owner_id=TEST_MEMBER_ID)
        supabase_mock.set_data("houses", [house])
        supabase_mock.set_data("house_members", [make_house_member()])
        supabase_mock.set_data("devices", [d1, d2])

        res = client.get("/api/v1/devices/")

        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_returns_empty_when_no_house(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [])
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("devices", [])

        res = client.get("/api/v1/devices/")

        assert res.status_code == 200
        assert res.json() == []


class TestGetDevice:
    def test_returns_single_device(self, client: TestClient, supabase_mock: SupabaseMock):
        house = make_house()
        device = make_device()
        supabase_mock.set_data("houses", [house])
        supabase_mock.set_data("house_members", [make_house_member()])
        supabase_mock.set_data("devices", [device])

        res = client.get(f"/api/v1/devices/{device['id']}")

        assert res.status_code == 200
        assert res.json()["id"] == device["id"]

    def test_returns_404_when_not_found(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member()])
        supabase_mock.set_data("devices", [])

        res = client.get("/api/v1/devices/nonexistent-id")

        assert res.status_code == 404


class TestVincularDevice:
    def test_vincular_success(self, client: TestClient, supabase_mock: SupabaseMock):
        house = make_house()
        device = make_device()
        supabase_mock.set_data("houses", [house])
        supabase_mock.set_data("house_members", [make_house_member()])
        supabase_mock.set_data("devices", [device])

        payload = {
            "ip": "192.168.1.101",
            "mac": "AA:BB:CC:DD:EE:01",
            "hostname": "luz-cocina",
            "tipo": "Luz",
            "name": "Luz cocina",
        }

        res = client.post("/api/v1/devices/vincular", json=payload)

        assert res.status_code == 200

    def test_vincular_fails_without_house(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [])
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("devices", [])

        payload = {
            "ip": "192.168.1.102",
            "mac": "AA:BB:CC:DD:EE:02",
            "hostname": "test",
            "tipo": "Luz",
            "name": "Luz test",
        }

        res = client.post("/api/v1/devices/vincular", json=payload)
        assert res.status_code == 400


class TestDesvincularDevice:
    def test_desvincular_success(self, client: TestClient, supabase_mock: SupabaseMock):
        device = make_device()
        supabase_mock.set_data("devices", [device])

        res = client.delete(f"/api/v1/devices/{device['id']}")

        assert res.status_code == 200
        assert res.json() == {"ok": True}

    def test_desvincular_not_found(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("devices", [])

        res = client.delete("/api/v1/devices/nonexistent-id")

        assert res.status_code == 404


class TestGetAllDevices:
    def test_returns_house_devices_for_user(self, client: TestClient, supabase_mock: SupabaseMock):
        """Bot endpoint filters by house, not individual owner."""
        house = make_house()
        d1 = make_device(owner_id=TEST_USER_ID)
        d2 = make_device(owner_id=TEST_MEMBER_ID, mac="BB:BB:BB:BB:BB:BB")
        supabase_mock.set_data("houses", [house])
        supabase_mock.set_data("devices", [d1, d2])

        res = client.get(
            f"/api/v1/devices/all?user_id={TEST_USER_ID}",
            headers=WEBHOOK_HEADERS,
        )

        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_requires_webhook_token(self, client: TestClient):
        res = client.get("/api/v1/devices/all")
        assert res.status_code == 401

    def test_returns_all_without_user_id(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("devices", [make_device()])

        res = client.get("/api/v1/devices/all", headers=WEBHOOK_HEADERS)

        assert res.status_code == 200
        assert isinstance(res.json(), list)


class TestUpdateStatus:
    def test_update_status_success(self, client: TestClient, supabase_mock: SupabaseMock):
        device = make_device()
        supabase_mock.set_data("devices", [device])

        res = client.patch(
            f"/api/v1/devices/{device['id']}/status",
            json={"is_online": True, "estado": {"power": "on"}},
            headers=WEBHOOK_HEADERS,
        )

        assert res.status_code == 200
        assert res.json() == {"ok": True}

    def test_update_status_requires_webhook_token(self, client: TestClient):
        res = client.patch(
            "/api/v1/devices/some-id/status",
            json={"is_online": True, "estado": {}},
        )
        assert res.status_code == 401

    def test_update_status_not_found(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("devices", [])

        res = client.patch(
            "/api/v1/devices/nonexistent/status",
            json={"is_online": False, "estado": {}},
            headers=WEBHOOK_HEADERS,
        )

        assert res.status_code == 404


class TestGetDeviceStatus:
    def test_returns_status(self, client: TestClient, supabase_mock: SupabaseMock):
        device = make_device(estado={"power": "on"})
        supabase_mock.set_data("devices", [device])

        res = client.get(
            f"/api/v1/devices/{device['id']}/status",
            headers=WEBHOOK_HEADERS,
        )

        assert res.status_code == 200
        data = res.json()
        assert data["is_online"] is True
        assert "estado" in data

    def test_requires_webhook_token(self, client: TestClient):
        res = client.get("/api/v1/devices/some-id/status")
        assert res.status_code == 401

    def test_returns_404_when_not_found(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("devices", [])

        res = client.get("/api/v1/devices/nonexistent/status", headers=WEBHOOK_HEADERS)
        assert res.status_code == 404


class TestHaConnection:
    def test_get_connection_not_connected(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("ha_integrations", [])

        res = client.get("/api/v1/devices/ha/connection")

        assert res.status_code == 200
        assert res.json()["connected"] is False

    def test_get_connection_connected(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("ha_integrations", [{
            "ha_url": "http://192.168.1.50:8123",
            "created_at": "2026-04-19T10:00:00+00:00",
        }])

        res = client.get("/api/v1/devices/ha/connection")

        assert res.status_code == 200
        assert res.json()["connected"] is True

    def test_delete_connection(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("ha_integrations", [{"user_id": TEST_USER_ID}])
        supabase_mock.set_data("devices", [])

        res = client.delete("/api/v1/devices/ha/connection")

        assert res.status_code == 200
        assert res.json()["ok"] is True

    def test_connect_ha_invalid_server(self, client: TestClient):
        import requests as req
        with patch("app.services.devices.requests.get", side_effect=req.ConnectionError):
            res = client.post(
                "/api/v1/devices/ha/connect",
                json={"ha_url": "http://invalid-host:8123", "token": "fake-token"},
            )
        assert res.status_code == 400

    def test_connect_ha_success(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member()])
        supabase_mock.set_data("ha_integrations", [])
        supabase_mock.set_data("devices", [make_device()])

        mock_api = MagicMock()
        mock_api.raise_for_status = lambda: None

        mock_states = MagicMock()
        mock_states.raise_for_status = lambda: None
        mock_states.json.return_value = [
            {"entity_id": "light.salon",  "state": "on",  "attributes": {"friendly_name": "Luz salón"}},
            {"entity_id": "switch.cocina","state": "off", "attributes": {"friendly_name": "Enchufe cocina"}},
            {"entity_id": "sensor.temp",  "state": "22",  "attributes": {}},  # skipped
        ]

        with patch("app.services.devices.requests.get", side_effect=[mock_api, mock_states]):
            res = client.post(
                "/api/v1/devices/ha/connect",
                json={"ha_url": "http://192.168.1.50:8123", "token": "valid-token"},
            )

        assert res.status_code == 200
        assert res.json()["importados"] == 2


class TestSendCommand:
    def test_send_command_blocked_without_house(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("house_members", [])
        supabase_mock.set_data("houses", [])

        res = client.post(
            "/api/v1/devices/some-id/command",
            json={"accion": "encender", "payload": {}},
        )
        assert res.status_code == 403

    def test_send_command_device_not_found(self, client: TestClient, supabase_mock: SupabaseMock):
        supabase_mock.set_data("houses", [make_house()])
        supabase_mock.set_data("house_members", [make_house_member()])
        supabase_mock.set_data("devices", [])

        with patch("app.services.devices.send_xmpp_message", new_callable=AsyncMock):
            res = client.post(
                "/api/v1/devices/nonexistent/command",
                json={"accion": "encender", "payload": {}},
            )

        assert res.status_code == 404
