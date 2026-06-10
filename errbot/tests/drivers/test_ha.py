from unittest.mock import MagicMock, patch

import pytest


def _device():
    return {"config": {"ha_url": "http://ha", "token": "tk", "entity_id": "light.foo"}}


@pytest.mark.parametrize("kwargs", [
    {"ha_url": "", "token": "tk", "entity_id": "light.foo"},
    {"ha_url": "http://x", "token": "tk", "entity_id": ""},
])
def test_ha_config_rejects_missing_fields(kwargs):
    from drivers.ha_driver import HAConfig
    with pytest.raises(ValueError):
        HAConfig(**kwargs)


def test_ha_config_from_dict_rejects_empty_dict():
    from drivers.ha_driver import HAConfig
    with pytest.raises(ValueError):
        HAConfig.from_dict({})


@pytest.mark.parametrize("state, expected_power, expected_online", [
    ("on", True, True),
    ("off", False, True),
])
def test_get_status_maps_known_states_to_power_field(state, expected_power, expected_online):
    from drivers.ha_driver import HomeAssistantDriver
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"state": state, "attributes": {"brightness": 80}}
    with patch("requests.get", return_value=mock_resp):
        result = HomeAssistantDriver().get_status(_device())
    assert result["is_online"] is expected_online
    assert result["estado"]["power"] is expected_power


def test_get_status_reports_offline_when_entity_unavailable():
    from drivers.ha_driver import HomeAssistantDriver
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"state": "unavailable", "attributes": {}}
    with patch("requests.get", return_value=mock_resp):
        assert HomeAssistantDriver().get_status(_device())["is_online"] is False


def test_get_status_reports_offline_on_network_exception():
    from drivers.ha_driver import HomeAssistantDriver
    with patch("requests.get", side_effect=RuntimeError("net")):
        result = HomeAssistantDriver().get_status(_device())
    assert result["is_online"] is False and "net" in result["error"]


@pytest.mark.parametrize("action_call, expected_service, expected_payload", [
    (("apagar", ()), "light/turn_off", None),
    (("brillo", (50,)), "light/turn_on", {"brightness_pct": 50}),
])
def test_actions_route_to_correct_service_call(action_call, expected_service, expected_payload):
    from drivers.ha_driver import HomeAssistantDriver
    action, extra_args = action_call

    with patch.object(HomeAssistantDriver, "_call_service", return_value={"ok": True}) as mock_call:
        getattr(HomeAssistantDriver(), action)(_device(), *extra_args)

    args = mock_call.call_args[0]
    assert args[1] == expected_service
    if expected_payload is not None:
        assert args[2] == expected_payload
