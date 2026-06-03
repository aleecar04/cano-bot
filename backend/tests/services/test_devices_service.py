from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
import asyncio
import pytest

from app.services import devices as dev_service
from app.models.drivers import DriverType


def _run(coro):
    return asyncio.run(coro)


# ── inferir_driver / inferir_config (puro, sin mocks) ───────────────────────

class TestInferirDriver:

    def test_smarttv_con_lg_devuelve_lg(self):
        assert dev_service.inferir_driver("SmartTV", "lg-living-room") == DriverType.LG_TV

    def test_smarttv_con_samsung_devuelve_samsung(self):
        assert dev_service.inferir_driver("SmartTV", "samsung-tv") == DriverType.SAMSUNG_TV

    def test_luz_va_a_tuya(self):
        assert dev_service.inferir_driver("Luz") == DriverType.TUYA

    def test_enchufe_va_a_tuya(self):
        assert dev_service.inferir_driver("Enchufe") == DriverType.TUYA

    def test_tipo_HA_va_a_tuya(self):
        assert dev_service.inferir_driver("light") == DriverType.TUYA
        assert dev_service.inferir_driver("switch") == DriverType.TUYA

    def test_tipo_desconocido_devuelve_none(self):
        assert dev_service.inferir_driver("Inventado") is None


class TestInferirConfig:

    def test_luz_lleva_channel(self):
        assert dev_service.inferir_config("Luz") == {"channel": 0}

    def test_smarttv_devuelve_vacio(self):
        assert dev_service.inferir_config("SmartTV") == {}


# ── vincular_device ─────────────────────────────────────────────────────────

class TestVincularDevice:

    def _device_in(self):
        from app.models.devices import DeviceVincular
        return DeviceVincular(
            name="Lampara", tipo="Luz", ip="192.168.1.10",
            mac="AA:BB:CC:DD:EE:FF", hostname="lampara.local",
        )

    def test_sin_house_lanza_400(self):
        with patch("app.services.devices.get_house_id_for_user", return_value=None):
            with pytest.raises(HTTPException) as exc:
                dev_service.vincular_device(self._device_in(), "u1")
            assert exc.value.status_code == 400

    def test_conflict_de_nombre_lanza_409(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_db.table.return_value.upsert.return_value.execute.side_effect = Exception(
                "duplicate house_id_name"
            )
            with pytest.raises(HTTPException) as exc:
                dev_service.vincular_device(self._device_in(), "u1")
            assert exc.value.status_code == 409

    def test_otra_excepcion_lanza_500(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_db.table.return_value.upsert.return_value.execute.side_effect = Exception(
                "random error"
            )
            with pytest.raises(HTTPException) as exc:
                dev_service.vincular_device(self._device_in(), "u1")
            assert exc.value.status_code == 500

    def test_sin_data_lanza_500(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_result = MagicMock(data=None)
            mock_db.table.return_value.upsert.return_value.execute.return_value = mock_result
            with pytest.raises(HTTPException) as exc:
                dev_service.vincular_device(self._device_in(), "u1")
            assert exc.value.status_code == 500

    def test_ok_devuelve_device(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_result = MagicMock(data=[{"id": "d1"}])
            mock_db.table.return_value.upsert.return_value.execute.return_value = mock_result
            result = dev_service.vincular_device(self._device_in(), "u1")
        assert result == {"id": "d1"}


# ── get_devices_for_house ───────────────────────────────────────────────────

class TestGetDevicesForHouse:

    def test_devuelve_devices_no_HA(self):
        with patch("app.services.devices.device_repository") as mock_d, \
             patch("app.services.devices.ha_integration_repository") as mock_ha:
            mock_d.find_by_house.return_value = [
                {"id": "d1", "driver": "tuya", "config": {}},
            ]
            mock_ha.find_credentials_by_house.return_value = None
            result = dev_service.get_devices_for_house("h1")
        assert result == [{"id": "d1", "driver": "tuya", "config": {}}]

    def test_HA_devices_enriquecidos_con_creds(self):
        with patch("app.services.devices.device_repository") as mock_d, \
             patch("app.services.devices.ha_integration_repository") as mock_ha:
            mock_d.find_by_house.return_value = [
                {"id": "d1", "driver": "homeassistant", "ha_entity_id": "light.x"},
            ]
            mock_ha.find_credentials_by_house.return_value = {
                "ha_url": "http://ha", "token": "tk",
            }
            result = dev_service.get_devices_for_house("h1")
        assert result[0]["config"]["ha_url"] == "http://ha"
        assert result[0]["config"]["entity_id"] == "light.x"


# ── get_devices / get_device / desvincular / update_device ──────────────────

class TestGetDevices:

    def test_devuelve_devices(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.device_repository") as mock_d:
            mock_d.find_by_house.return_value = [{"id": "d1"}]
            assert dev_service.get_devices("u1") == [{"id": "d1"}]

    def test_sin_house_devuelve_vacio(self):
        with patch("app.services.devices.get_house_id_for_user", return_value=None):
            assert dev_service.get_devices("u1") == []


class TestGetDevice:

    def test_devuelve_device(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.device_repository") as mock_d:
            mock_d.find_by_id_and_house.return_value = {"id": "d1"}
            assert dev_service.get_device("d1", "u1") == {"id": "d1"}


class TestDesvincularDevice:

    def test_devuelve_false_si_no_existe(self):
        with patch("app.services.devices.get_user_role", return_value="member"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_chain = MagicMock()
            mock_chain.data = []
            mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = mock_chain
            assert dev_service.desvincular_device("d1", "u1") is False

    def test_devuelve_true_si_borra(self):
        with patch("app.services.devices.get_user_role", return_value="member"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_chain = MagicMock()
            mock_chain.data = [{"id": "d1"}]
            mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = mock_chain
            assert dev_service.desvincular_device("d1", "u1") is True

    def test_owner_borra_por_house_id(self):
        with patch("app.services.devices.get_user_role", return_value="owner"), \
             patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.supabase") as mock_db:
            mock_chain = MagicMock()
            mock_chain.data = [{"id": "d1"}]
            mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = mock_chain
            assert dev_service.desvincular_device("d1", "u1") is True


# ── send_group_command (validation) ─────────────────────────────────────────

class TestSendGroupCommand:

    def test_accion_invalida_lanza_400(self):
        with pytest.raises(HTTPException) as exc:
            _run(dev_service.send_group_command("room", "r1", "brillo", "u1"))
        assert exc.value.status_code == 400

    def test_scope_vacio_lanza_404(self):
        # find_devices_in_scope lanza HTTPException(404) si vacío
        with patch("app.services.devices.find_devices_in_scope",
                   side_effect=HTTPException(status_code=404, detail="vacío")):
            with pytest.raises(HTTPException) as exc:
                _run(dev_service.send_group_command("room", "r1", "encender", "u1"))
            assert exc.value.status_code == 404


# ── HA ──────────────────────────────────────────────────────────────────────

class TestGetHaConnection:

    def test_no_connected(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.ha_integration_repository") as mock_ha:
            mock_ha.find_summary_by_house.return_value = None
            result = dev_service.get_ha_connection("u1")
        assert result["connected"] is False

    def test_connected(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.ha_integration_repository") as mock_ha:
            mock_ha.find_summary_by_house.return_value = {
                "ha_url": "http://ha", "created_at": "2025-01-01",
            }
            result = dev_service.get_ha_connection("u1")
        assert result["connected"] is True
        assert result["ha_url"] == "http://ha"


class TestDisconnectHa:

    def test_sin_house_no_hace_nada(self):
        """disconnect_ha es silencioso si el usuario no tiene casa (early return)."""
        with patch("app.services.devices.get_house_id_for_user", return_value=None):
            dev_service.disconnect_ha("u1")  # no lanza

    def test_con_house_borra(self):
        with patch("app.services.devices.get_house_id_for_user", return_value="h1"), \
             patch("app.services.devices.require_owner"), \
             patch("app.services.devices.supabase") as mock_db:
            dev_service.disconnect_ha("u1")
        mock_db.table.assert_called()
