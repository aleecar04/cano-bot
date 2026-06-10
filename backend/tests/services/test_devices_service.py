import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.drivers import DriverType
from app.services import devices as dev_service


def _run(coro):
    return asyncio.run(coro)


# ── inferir_driver / inferir_config ─────────────────────────────────────────

@pytest.mark.parametrize("tipo, hostname, expected", [
    ("SmartTV", "lg-living-room", DriverType.LG_TV),
    ("SmartTV", "samsung-tv", DriverType.SAMSUNG_TV),
    ("SmartTV", "sony-bravia", None),
    ("Luz", None, DriverType.TUYA),
    ("light", None, DriverType.TUYA),
    ("Altavoz", None, None),
    ("Inventado", None, None),
    ("", None, None),
])
def test_inferir_driver_maps_type_or_hostname_to_driver(tipo, hostname, expected):
    assert dev_service.inferir_driver(tipo, hostname) == expected


@pytest.mark.parametrize("tipo, expected", [
    ("Luz", {"channel": 0}),
    ("IoT", {"channel": 0}),
    ("SmartTV", {}),
    ("Nevera", {}),
])
def test_inferir_config_returns_channel_for_lights_else_empty(tipo, expected):
    assert dev_service.inferir_config(tipo) == expected


# ── vincular_device ─────────────────────────────────────────────────────────

class TestVincularDevice:

    def _device_in(self):
        from app.models.devices import DeviceVincular
        return DeviceVincular(
            name="Lampara", tipo="Luz", ip="192.168.1.10",
            mac="AA:BB:CC:DD:EE:FF", hostname="lampara.local",
        )

    def test_user_without_house_raises_400(self):
        with patch("app.services.devices.get_house_id_for_user", return_value=None), \
             pytest.raises(HTTPException) as exc:
            dev_service.vincular_device(self._device_in(), "u1")
        assert exc.value.status_code == 400

    @pytest.mark.parametrize("exc_msg, expected_status", [
        ("duplicate house_id_name", 409),
        ("random error", 500),
    ])
    def test_db_errors_translate_to_http_status(self, exc_msg, expected_status):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_db.table.return_value.upsert.return_value.execute.side_effect = Exception(exc_msg)
            with pytest.raises(HTTPException) as exc:
                dev_service.vincular_device(self._device_in(), "u1")
            assert exc.value.status_code == expected_status

    def test_returns_device_on_success(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{"id": "d1"}])
            assert dev_service.vincular_device(self._device_in(), "u1") == {"id": "d1"}


# ── get_devices_for_house ───────────────────────────────────────────────────

class TestGetDevicesForHouse:

    def test_returns_devices_unchanged_when_no_ha_credentials(self):
        with patch("app.services.devices.device_repository") as mock_d, \
             patch("app.services.devices.ha_integration_repository") as mock_ha:
            mock_d.find_by_house.return_value = [{"id": "d1", "driver": "tuya", "config": {}}]
            mock_ha.find_credentials_by_house.return_value = None
            assert dev_service.get_devices_for_house("h1") == [{"id": "d1", "driver": "tuya", "config": {}}]

    def test_homeassistant_devices_are_enriched_with_credentials(self):
        with patch("app.services.devices.device_repository") as mock_d, \
             patch("app.services.devices.ha_integration_repository") as mock_ha:
            mock_d.find_by_house.return_value = [
                {"id": "d1", "driver": "homeassistant", "ha_entity_id": "light.x"},
            ]
            mock_ha.find_credentials_by_house.return_value = {"ha_url": "http://ha", "token": "tk"}
            result = dev_service.get_devices_for_house("h1")
        assert result[0]["config"]["ha_url"] == "http://ha"
        assert result[0]["config"]["entity_id"] == "light.x"


# ── get_devices / get_device ────────────────────────────────────────────────

class TestGetDevices:

    def test_returns_devices_when_house_exists(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.device_repository") as mock_d:
            mock_d.find_by_house.return_value = [{"id": "d1"}]
            assert dev_service.get_devices("u1") == [{"id": "d1"}]

def test_get_device_returns_device_in_user_house():
    with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
         patch("app.services.devices.device_repository") as mock_d:
        mock_d.find_by_id_and_house.return_value = {"id": "d1"}
        assert dev_service.get_device("d1", "u1") == {"id": "d1"}


# ── desvincular_device ──────────────────────────────────────────────────────

class TestDesvincularDevice:

    def _patch_delete(self, data):
        return patch("app.services.devices.supabase",
                     **{"return_value.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value": MagicMock(data=data)})

    @pytest.mark.parametrize("data, expected", [
        ([], False),
        ([{"id": "d1"}], True),
    ])
    def test_member_returns_outcome_of_delete(self, data, expected):
        with patch("app.services.devices.get_user_role", return_value="member"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=data)
            assert dev_service.desvincular_device("d1", "u1") is expected

# ── send_group_command (validation) ─────────────────────────────────────────

class TestSendGroupCommand:

    def test_invalid_action_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            _run(dev_service.send_group_command("room", "r1", "brillo", "u1"))
        assert exc.value.status_code == 400

# ── HA integration ──────────────────────────────────────────────────────────

class TestHaIntegration:

    @pytest.mark.parametrize("summary, expected_connected", [
        (None, False),
        ({"ha_url": "http://ha", "created_at": "2025-01-01"}, True),
    ])
    def test_get_ha_connection_reflects_credentials_presence(self, summary, expected_connected):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.ha_integration_repository") as mock_ha:
            mock_ha.find_summary_by_house.return_value = summary
            result = dev_service.get_ha_connection("u1")
        assert result["connected"] is expected_connected
        if expected_connected:
            assert result["ha_url"] == "http://ha"

