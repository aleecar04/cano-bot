import pytest
from unittest.mock import patch, MagicMock


# ── TuyaConfig dataclass ─────────────────────────────────────────────────────

class TestTuyaConfigValidation:

    def test_construye_con_los_3_campos(self):
        from drivers.tuya_driver import TuyaConfig
        cfg = TuyaConfig(dev_id="abc", local_key="key123", version=3.4)
        assert cfg.dev_id == "abc"
        assert cfg.local_key == "key123"
        assert cfg.version == 3.4

    def test_version_tiene_default_34(self):
        from drivers.tuya_driver import TuyaConfig
        cfg = TuyaConfig(dev_id="abc", local_key="key123")
        assert cfg.version == 3.4

    def test_lanza_si_falta_dev_id(self):
        from drivers.tuya_driver import TuyaConfig
        with pytest.raises(ValueError, match="dev_id"):
            TuyaConfig(dev_id="", local_key="key123")

    def test_lanza_si_falta_local_key(self):
        from drivers.tuya_driver import TuyaConfig
        with pytest.raises(ValueError, match="local_key"):
            TuyaConfig(dev_id="abc", local_key="")

    def test_es_inmutable(self):
        from drivers.tuya_driver import TuyaConfig
        cfg = TuyaConfig(dev_id="abc", local_key="key123")
        with pytest.raises(Exception):
            cfg.dev_id = "otra"


class TestTuyaConfigFromDict:

    def test_construye_desde_dict_completo(self):
        from drivers.tuya_driver import TuyaConfig
        cfg = TuyaConfig.from_dict({"dev_id": "a", "local_key": "b", "version": 3.3})
        assert cfg == TuyaConfig(dev_id="a", local_key="b", version=3.3)

    def test_aplica_version_default_si_falta(self):
        from drivers.tuya_driver import TuyaConfig
        cfg = TuyaConfig.from_dict({"dev_id": "a", "local_key": "b"})
        assert cfg.version == 3.4

    def test_ignora_claves_extra(self):
        """Casos como config={'channel': 0, 'dev_id': 'a', ...} no deben petar."""
        from drivers.tuya_driver import TuyaConfig
        cfg = TuyaConfig.from_dict({"dev_id": "a", "local_key": "b", "channel": 0, "extra": "x"})
        assert cfg.dev_id == "a"

    def test_levanta_si_dict_incompleto(self):
        from drivers.tuya_driver import TuyaConfig
        with pytest.raises(ValueError):
            TuyaConfig.from_dict({"channel": 0})


# ── TuyaDriver public methods ────────────────────────────────────────────────

class TestTuyaDriverEncenderApagar:

    def _device(self):
        return {
            "id": "d1", "type": "Enchufe", "ip": "192.168.1.10",
            "config": {"dev_id": "abc", "local_key": "k1", "version": 3.4},
        }

    def test_encender_ok_devuelve_ok_true(self):
        from drivers.tuya_driver import TuyaDriver
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"dps": {"1": False}}
            mock_get.return_value = mock_dev
            result = TuyaDriver().encender(self._device())
        assert result == {"ok": True}
        mock_dev.turn_on.assert_called_once()

    def test_apagar_ok_devuelve_ok_true(self):
        from drivers.tuya_driver import TuyaDriver
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"dps": {"1": True}}
            mock_get.return_value = mock_dev
            result = TuyaDriver().apagar(self._device())
        assert result == {"ok": True}
        mock_dev.turn_off.assert_called_once()

    def test_encender_captura_excepcion_y_devuelve_error(self):
        from drivers.tuya_driver import TuyaDriver
        with patch.object(TuyaDriver, "_get_device", side_effect=RuntimeError("net")):
            result = TuyaDriver().encender(self._device())
        assert result["ok"] is False
        assert "net" in result["error"]


class TestTuyaDriverBrillo:

    def _bulb(self):
        return {
            "id": "b1", "type": "Luz", "ip": "192.168.1.20",
            "config": {"dev_id": "abc", "local_key": "k1"},
        }

    def test_brillo_rechazado_en_no_bulb(self):
        from drivers.tuya_driver import TuyaDriver
        dev = {"type": "Enchufe", "config": {"dev_id": "x", "local_key": "y"}}
        result = TuyaDriver().brillo(dev, 50)
        assert result["ok"] is False
        assert "brillo" in result["error"].lower()

    def test_brillo_valido_escribe_dps_22(self):
        from drivers.tuya_driver import TuyaDriver
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"dps": {}}
            mock_get.return_value = mock_dev
            result = TuyaDriver().brillo(self._bulb(), 50)
        assert result == {"ok": True, "brillo": 50}
        mock_dev.set_value.assert_called_once_with(22, 500)  # 50 * 10

    def test_brillo_clampa_a_rango_tuya(self):
        from drivers.tuya_driver import TuyaDriver
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"dps": {}}
            mock_get.return_value = mock_dev
            TuyaDriver().brillo(self._bulb(), 200)  # mayor que máximo
        called_value = mock_dev.set_value.call_args[0][1]
        assert called_value == 1000  # capped


class TestTuyaDriverGetStatusSensor:

    def test_sensor_devuelve_temp_humidity_battery(self):
        from drivers.tuya_driver import TuyaDriver
        dev = {
            "type": "Sensor", "ip": "192.168.1.30",
            "config": {"dev_id": "x", "local_key": "y"},
        }
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"dps": {"1": 235, "2": 48, "4": 92}}
            mock_get.return_value = mock_dev
            result = TuyaDriver().get_status(dev)
        assert result["is_online"] is True
        assert result["estado"]["temperature"] == 23.5
        assert result["estado"]["humidity"] == 48
        assert result["estado"]["battery"] == 92


class TestTuyaDriverGetStatusOffline:

    def test_marca_offline_si_status_es_error(self):
        from drivers.tuya_driver import TuyaDriver
        dev = {
            "type": "Enchufe", "ip": "192.168.1.40",
            "config": {"dev_id": "x", "local_key": "y"},
        }
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"Error": "timeout"}
            mock_get.return_value = mock_dev
            result = TuyaDriver().get_status(dev)
        assert result["is_online"] is False
