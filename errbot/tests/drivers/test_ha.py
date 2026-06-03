import pytest
from unittest.mock import patch, MagicMock


# ── HAConfig dataclass ───────────────────────────────────────────────────────

class TestHAConfigValidation:

    def test_construye_con_los_3_campos(self):
        from drivers.ha_driver import HAConfig
        cfg = HAConfig(ha_url="http://x", token="tk", entity_id="light.foo")
        assert cfg.ha_url == "http://x"
        assert cfg.token == "tk"
        assert cfg.entity_id == "light.foo"

    def test_lanza_si_falta_ha_url(self):
        from drivers.ha_driver import HAConfig
        with pytest.raises(ValueError, match="ha_url"):
            HAConfig(ha_url="", token="tk", entity_id="light.foo")

    def test_lanza_si_falta_token(self):
        from drivers.ha_driver import HAConfig
        with pytest.raises(ValueError, match="token"):
            HAConfig(ha_url="http://x", token="", entity_id="light.foo")

    def test_lanza_si_falta_entity_id(self):
        from drivers.ha_driver import HAConfig
        with pytest.raises(ValueError, match="entity_id"):
            HAConfig(ha_url="http://x", token="tk", entity_id="")


class TestHAConfigFromDict:

    def test_construye_desde_dict_completo(self):
        from drivers.ha_driver import HAConfig
        cfg = HAConfig.from_dict({
            "ha_url": "http://x", "token": "tk", "entity_id": "switch.foo"
        })
        assert cfg.ha_url == "http://x"

    def test_levanta_si_dict_incompleto(self):
        from drivers.ha_driver import HAConfig
        with pytest.raises(ValueError):
            HAConfig.from_dict({})


# ── HomeAssistantDriver ──────────────────────────────────────────────────────

class TestHomeAssistantDriverGetStatus:

    def _device(self):
        return {
            "config": {"ha_url": "http://ha", "token": "tk", "entity_id": "light.foo"}
        }

    def test_get_status_normal_devuelve_power_state_attributes(self):
        from drivers.ha_driver import HomeAssistantDriver
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "state": "on",
            "attributes": {"friendly_name": "Foo", "brightness": 80},
        }
        with patch("requests.get", return_value=mock_resp):
            result = HomeAssistantDriver().get_status(self._device())
        assert result["is_online"] is True
        assert result["estado"]["power"] is True
        assert result["estado"]["state"] == "on"
        assert result["estado"]["attributes"]["brightness"] == 80

    def test_get_status_off_marca_power_false(self):
        from drivers.ha_driver import HomeAssistantDriver
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"state": "off", "attributes": {}}
        with patch("requests.get", return_value=mock_resp):
            result = HomeAssistantDriver().get_status(self._device())
        assert result["estado"]["power"] is False

    def test_get_status_unavailable_marca_offline(self):
        from drivers.ha_driver import HomeAssistantDriver
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"state": "unavailable", "attributes": {}}
        with patch("requests.get", return_value=mock_resp):
            result = HomeAssistantDriver().get_status(self._device())
        assert result["is_online"] is False

    def test_get_status_excepcion_marca_offline(self):
        from drivers.ha_driver import HomeAssistantDriver
        with patch("requests.get", side_effect=RuntimeError("net")):
            result = HomeAssistantDriver().get_status(self._device())
        assert result["is_online"] is False
        assert "net" in result["error"]


class TestHomeAssistantDriverAcciones:

    def _device(self):
        return {
            "config": {"ha_url": "http://ha", "token": "tk", "entity_id": "light.foo"}
        }

    def test_encender_llama_a_turn_on(self):
        from drivers.ha_driver import HomeAssistantDriver
        with patch.object(HomeAssistantDriver, "_call_service") as mock_call:
            mock_call.return_value = {"ok": True}
            HomeAssistantDriver().encender(self._device())
        assert mock_call.call_args[0][1] == "light/turn_on"

    def test_apagar_llama_a_turn_off(self):
        from drivers.ha_driver import HomeAssistantDriver
        with patch.object(HomeAssistantDriver, "_call_service") as mock_call:
            mock_call.return_value = {"ok": True}
            HomeAssistantDriver().apagar(self._device())
        assert mock_call.call_args[0][1] == "light/turn_off"

    def test_brillo_pasa_brightness_pct(self):
        from drivers.ha_driver import HomeAssistantDriver
        with patch.object(HomeAssistantDriver, "_call_service") as mock_call:
            mock_call.return_value = {"ok": True}
            HomeAssistantDriver().brillo(self._device(), 50)
        assert mock_call.call_args[0][1] == "light/turn_on"
        assert mock_call.call_args[0][2] == {"brightness_pct": 50}
