from unittest.mock import MagicMock, patch


def test_get_all_calls_devices_endpoint_and_returns_device_list():
    from api import devices
    mock_resp = MagicMock(); mock_resp.json.return_value = [{"id": "a"}, {"id": "b"}]
    with patch("api._client.get", return_value=mock_resp) as mock_get:
        assert devices.get_all() == [{"id": "a"}, {"id": "b"}]
    assert mock_get.call_args[0][0] == "/api/v1/devices/all"


def test_patch_status_sends_status_payload_to_device_path():
    from api import devices
    with patch("api._client.patch") as mock_patch:
        devices.patch_status("dev-1", True, {"power": "on"})
    assert mock_patch.call_args[0][0] == "/api/v1/devices/dev-1/status"
    assert mock_patch.call_args.kwargs["json"] == {
        "is_online": True, "estado": {"power": "on"},
    }


def test_patch_config_sends_payload():
    from api import devices
    with patch("api._client.patch") as mock_patch:
        devices.patch_config("dev-1", {"client_key": "abc"})
    assert mock_patch.call_args[0][0] == "/api/v1/devices/dev-1/config"
    assert mock_patch.call_args.kwargs["json"] == {"client_key": "abc"}
