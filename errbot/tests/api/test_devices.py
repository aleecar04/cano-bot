from unittest.mock import patch, MagicMock


class TestGetAll:

    def test_returns_device_list(self):
        from api import devices
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": "a"}, {"id": "b"}]
        with patch("api._client.get", return_value=mock_resp):
            assert devices.get_all() == [{"id": "a"}, {"id": "b"}]

    def test_calls_devices_all_endpoint(self):
        from api import devices
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        with patch("api._client.get", return_value=mock_resp) as mock_get:
            devices.get_all()
        assert mock_get.call_args[0][0] == "/api/v1/devices/all"


class TestPatchStatus:

    def test_sends_status_payload(self):
        from api import devices
        with patch("api._client.patch") as mock_patch:
            devices.patch_status("dev-1", True, {"power": "on"})
        path = mock_patch.call_args[0][0]
        assert path == "/api/v1/devices/dev-1/status"
        assert mock_patch.call_args.kwargs["json"] == {
            "is_online": True, "estado": {"power": "on"}
        }


class TestPatchConfig:

    def test_sends_config_payload(self):
        from api import devices
        with patch("api._client.patch") as mock_patch:
            devices.patch_config("dev-1", {"client_key": "abc"})
        path = mock_patch.call_args[0][0]
        assert path == "/api/v1/devices/dev-1/config"
        assert mock_patch.call_args.kwargs["json"] == {"client_key": "abc"}
