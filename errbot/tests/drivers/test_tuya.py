from unittest.mock import MagicMock, patch

import pytest

from drivers.tuya_driver import TuyaConfig, TuyaDriver


def _plug():
    return {
        "id": "device_enchufe", "type": "Enchufe", "ip": "192.168.1.10",
        "config": {"dev_id": "abc", "local_key": "k1", "version": 3.4},
    }


def _bulb():
    return {
        "id": "device_bombilla", "type": "Luz", "ip": "192.168.1.20",
        "config": {"dev_id": "abc", "local_key": "k1"},
    }


class TestTuyaDriver:

    def test_tuya_config_rejects_missing_fields(self):
        with pytest.raises(ValueError, match="dev_id"):
            TuyaConfig(dev_id="", local_key="key123")

    def test_tuya_config_from_dict(self):
        cfg = TuyaConfig.from_dict({"dev_id": "a", "local_key": "b", "version": 3.3})
        assert cfg == TuyaConfig(dev_id="a", local_key="b", version=3.3)

        assert TuyaConfig.from_dict({"dev_id": "a", "local_key": "b"}).version == 3.4
        assert TuyaConfig.from_dict({"dev_id": "a", "local_key": "b", "channel": 0}).dev_id == "a"

        with pytest.raises(ValueError):
            TuyaConfig.from_dict({"channel": 0})

    @pytest.mark.parametrize("method_name, current_dps, expected_method", [
        ("turn_on", {"1": False}, "turn_on"),
        ("turn_off", {"1": True}, "turn_off"),
    ])
    def test_power_actions(self, method_name, current_dps, expected_method):
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"dps": current_dps}
            mock_get.return_value = mock_dev
            assert getattr(TuyaDriver(), method_name)(_plug()) == {"ok": True}
        getattr(mock_dev, expected_method).assert_called_once()

    def test_power_action_returns_error_on_exception(self):
        with patch.object(TuyaDriver, "_get_device", side_effect=RuntimeError("net")):
            result = TuyaDriver().turn_on(_plug())
        assert result["ok"] is False and "net" in result["error"]

    def test_brightness_rejects_non_bulb_devices(self):
        plug = {"type": "Enchufe", "config": {"dev_id": "x", "local_key": "y"}}
        result = TuyaDriver().brightness(plug, 50)
        assert result["ok"] is False and "brillo" in result["error"].lower()

    def test_brightness_writes_scaled_dps(self):
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"dps": {}}
            mock_get.return_value = mock_dev
            TuyaDriver().brightness(_bulb(), 50)
        assert mock_dev.set_value.call_args[0] == (22, 500)

    def test_get_status_parses_sensor_dps(self):
        sensor = {"type": "Sensor", "ip": "192.168.1.30",
                  "config": {"dev_id": "x", "local_key": "y"}}
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"dps": {"1": 235, "2": 48, "4": 92}}
            mock_get.return_value = mock_dev
            result = TuyaDriver().get_status(sensor)
        assert result["is_online"] is True
        assert result["state"] == {"temperature": 23.5, "humidity": 48, "battery": 92}

    def test_get_status_reports_offline_on_error_response(self):
        plug = {"type": "Enchufe", "ip": "192.168.1.40",
                "config": {"dev_id": "x", "local_key": "y"}}
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"Error": "timeout"}
            mock_get.return_value = mock_dev
            assert TuyaDriver().get_status(plug)["is_online"] is False

    @pytest.mark.parametrize("method_name, args, dev_call, dev_call_args", [
        ("set_color_rgb", (50, 100, 200), "set_colour", (50, 100, 200)),
        ("color_temperature", (4000,), "set_colourtemp", (342,)),
    ])
    def test_bulb_actions_go_through_with_device(self, method_name, args, dev_call, dev_call_args):
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"dps": {"20": True}}
            mock_get.return_value = mock_dev
            result = getattr(TuyaDriver(), method_name)(_bulb(), *args)
        assert result["ok"] is True
        getattr(mock_dev, dev_call).assert_called_once_with(*dev_call_args)

    def test_get_status_bulb_parses_brightness_temp_hsv(self):
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"dps": {
                "20": True, "21": "colour", "22": 500, "23": 500,
                "24": "00780383ff03e8",
            }}
            mock_get.return_value = mock_dev
            estado = TuyaDriver().get_status(_bulb())["state"]
        assert estado["brightness"] == 50 and estado["work_mode"] == "colour"
        assert estado["color_temp"] == 4600 and estado["color_hex"].startswith("#")

    def test_with_device_returns_unreachable_when_status_has_error(self):
        with patch.object(TuyaDriver, "_get_device") as mock_get:
            mock_dev = MagicMock()
            mock_dev.status.return_value = {"Error": "timeout"}
            mock_get.return_value = mock_dev
            result = TuyaDriver().turn_on(_bulb())
        assert result["ok"] is False and "bombilla" in result["error"].lower()
