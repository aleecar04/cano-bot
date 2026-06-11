from unittest.mock import MagicMock, patch

import pytest

from drivers.ha_driver import HAConfig, HomeAssistantDriver


def _device():
    return {"config": {"ha_url": "http://ha", "token": "tk", "entity_id": "light.salon"}}


class TestHomeAssistantDriver:

    def test_ha_config_validate_fields(self):
        with pytest.raises(ValueError):
            HAConfig(ha_url="", token="tk", entity_id="light.salon")

    def test_get_status_maps_known_states_to_power_field(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"state": "on", "attributes": {"brightness": 80}}
        with patch("requests.get", return_value=mock_resp):
            result = HomeAssistantDriver().get_status(_device())
        assert result["is_online"] is True
        assert result["state"]["power"] is True

    def test_get_status_reports_offline_on_network_exception(self):
        with patch("requests.get", side_effect=RuntimeError("net")):
            result = HomeAssistantDriver().get_status(_device())
        assert result["is_online"] is False and "net" in result["error"]

    @pytest.mark.parametrize("action_call, expected_service, expected_payload", [
        (("turn_off", ()), "light/turn_off", None),
        (("brightness", (50,)), "light/turn_on", {"brightness_pct": 50}),
    ])
    def test_actions_route_to_correct_service_call(self, action_call, expected_service, expected_payload):
        action, extra_args = action_call

        with patch.object(HomeAssistantDriver, "_call_service", return_value={"ok": True}) as mock_call:
            getattr(HomeAssistantDriver(), action)(_device(), *extra_args)

        args = mock_call.call_args[0]
        assert args[1] == expected_service
        if expected_payload is not None:
            assert args[2] == expected_payload
