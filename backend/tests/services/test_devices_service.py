import asyncio
from app.services.home import home_service
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.devices import DeviceVincular
from app.models.drivers import DriverType
from app.services.devices import devices_service as dev_service


def _run(coro):
    return asyncio.run(coro)


class TestDevicesService:

    @pytest.mark.parametrize("tipo, hostname, expected", [
        ("SmartTV", "lg-living-room", DriverType.LG_TV),
        ("SmartTV", "sony-bravia", None),
        ("Luz", None, DriverType.TUYA),
        ("Altavoz", None, None),
    ])
    def test_inferir_driver_picks_lg_for_lg_hostname(self, tipo, hostname, expected):
        assert dev_service.inferir_driver(tipo, hostname) == expected

    @pytest.mark.parametrize("tipo, expected", [
        ("Luz", {"channel": 0}),
        ("SmartTV", {}),
    ])
    def test_inferir_config_returns_channel_only_for_lights(self, tipo, expected):
        assert dev_service.inferir_config(tipo) == expected

    def _device_in(self):
        return DeviceVincular(
            name="Lampara Salon", tipo="Luz", ip="192.168.1.10",
            mac="AA:BB:CC:DD:EE:FF", hostname="lampara.local",
        )

    def test_user_without_house_raises_400(self):
        with patch.object(home_service, "get_house_id_for_user", return_value=None), \
             pytest.raises(HTTPException) as exc:
            dev_service.vincular_device(self._device_in(), "user_anabel")
        assert exc.value.status_code == 400

    @pytest.mark.parametrize("exc_msg, expected_status", [
        ("duplicate house_id_name", 409),
        ("random error", 500),
    ])
    def test_duplicate_returns_409_unknown_returns_500(self, exc_msg, expected_status):
        with patch.object(home_service, "get_house_id_for_user", return_value="casa_demo"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_db.table.return_value.upsert.return_value.execute.side_effect = Exception(exc_msg)
            with pytest.raises(HTTPException) as exc:
                dev_service.vincular_device(self._device_in(), "user_anabel")
            assert exc.value.status_code == expected_status

    def test_returns_device_on_success(self):
        with patch.object(home_service, "get_house_id_for_user", return_value="casa_demo"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{"id": "device_lampara"}])
            assert dev_service.vincular_device(self._device_in(), "user_anabel") == {"id": "device_lampara"}

    def test_homeassistant_devices_enriched_with_creds(self):
        with patch("app.services.devices.device_repository") as mock_d, \
             patch("app.services.devices.ha_integration_repository") as mock_ha:
            mock_d.find_by_house.return_value = [
                {"id": "device_lampara", "driver": "homeassistant", "ha_entity_id": "light.x"},
            ]
            mock_ha.find_credentials_by_house.return_value = {"ha_url": "http://ha", "token": "tk"}
            result = dev_service.get_devices_for_house("casa_demo")
        assert result[0]["config"]["ha_url"] == "http://ha"
        assert result[0]["config"]["entity_id"] == "light.x"

    def test_returns_devices_when_house_exists(self):
        with patch.object(home_service, "get_house_id_for_user", return_value="casa_demo"), \
             patch("app.services.devices.device_repository") as mock_d:
            mock_d.find_by_house.return_value = [{"id": "device_lampara"}]
            assert dev_service.get_devices("user_anabel") == [{"id": "device_lampara"}]

    @pytest.mark.parametrize("data, expected", [
        ([], False),
        ([{"id": "device_lampara"}], True),
    ])
    def test_desvincular_returns_delete_outcome(self, data, expected):
        with patch.object(home_service, "get_user_role", return_value="member"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=data)
            assert dev_service.desvincular_device("device_lampara", "user_anabel") is expected

    @pytest.mark.parametrize("summary, expected_connected", [
        (None, False),
        ({"ha_url": "http://ha", "created_at": "2025-01-01"}, True),
    ])
    def test_get_ha_connection_uses_credentials(self, summary, expected_connected):
        with patch.object(home_service, "get_house_id_for_user", return_value="casa_demo"), \
             patch("app.services.devices.ha_integration_repository") as mock_ha:
            mock_ha.find_summary_by_house.return_value = summary
            result = dev_service.get_ha_connection("user_anabel")
        assert result["connected"] is expected_connected
        if expected_connected:
            assert result["ha_url"] == "http://ha"
