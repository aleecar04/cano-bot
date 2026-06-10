from unittest.mock import MagicMock, patch

import pytest


def _plug():
    return {
        "id": "d1", "type": "Enchufe", "ip": "192.168.1.10",
        "config": {"dev_id": "abc", "local_key": "k1", "version": 3.4},
    }


def _bulb():
    return {
        "id": "b1", "type": "Luz", "ip": "192.168.1.20",
        "config": {"dev_id": "abc", "local_key": "k1"},
    }


@pytest.mark.parametrize("dev_id, local_key, expected_msg", [
    ("", "key123", "dev_id"),
    ("abc", "", "local_key"),
])
def test_tuya_config_rejects_missing_fields(dev_id, local_key, expected_msg):
    from drivers.tuya_driver import TuyaConfig
    with pytest.raises(ValueError, match=expected_msg):
        TuyaConfig(dev_id=dev_id, local_key=local_key)


def test_tuya_config_from_dict():
    from drivers.tuya_driver import TuyaConfig

    cfg = TuyaConfig.from_dict({"dev_id": "a", "local_key": "b", "version": 3.3})
    assert cfg == TuyaConfig(dev_id="a", local_key="b", version=3.3)

    assert TuyaConfig.from_dict({"dev_id": "a", "local_key": "b"}).version == 3.4
    assert TuyaConfig.from_dict({"dev_id": "a", "local_key": "b", "channel": 0}).dev_id == "a"

    with pytest.raises(ValueError):
        TuyaConfig.from_dict({"channel": 0})


@pytest.mark.parametrize("action, current_dps, expected_method", [
    ("encender", {"1": False}, "turn_on"),
    ("apagar", {"1": True}, "turn_off"),
])
def test_power_actions_call_corresponding_device_method(action, current_dps, expected_method):
    from drivers.tuya_driver import TuyaDriver

    with patch.object(TuyaDriver, "_get_device") as mock_get:
        mock_dev = MagicMock()
        mock_dev.status.return_value = {"dps": current_dps}
        mock_get.return_value = mock_dev
        assert getattr(TuyaDriver(), action)(_plug()) == {"ok": True}
    getattr(mock_dev, expected_method).assert_called_once()


def test_power_action_returns_error_on_exception():
    from drivers.tuya_driver import TuyaDriver
    with patch.object(TuyaDriver, "_get_device", side_effect=RuntimeError("net")):
        result = TuyaDriver().encender(_plug())
    assert result["ok"] is False and "net" in result["error"]


def test_brillo_rejects_non_bulb_devices():
    from drivers.tuya_driver import TuyaDriver
    plug = {"type": "Enchufe", "config": {"dev_id": "x", "local_key": "y"}}
    result = TuyaDriver().brillo(plug, 50)
    assert result["ok"] is False and "brillo" in result["error"].lower()


@pytest.mark.parametrize("input_value, expected_dps_value", [
    (50, 500),
    (200, 1000),
])
def test_brillo_writes_dps_22_scaled_and_clamped(input_value, expected_dps_value):
    from drivers.tuya_driver import TuyaDriver
    with patch.object(TuyaDriver, "_get_device") as mock_get:
        mock_dev = MagicMock()
        mock_dev.status.return_value = {"dps": {}}
        mock_get.return_value = mock_dev
        TuyaDriver().brillo(_bulb(), input_value)
    assert mock_dev.set_value.call_args[0] == (22, expected_dps_value)


def test_get_status_parses_sensor_dps():
    from drivers.tuya_driver import TuyaDriver
    sensor = {"type": "Sensor", "ip": "192.168.1.30",
              "config": {"dev_id": "x", "local_key": "y"}}
    with patch.object(TuyaDriver, "_get_device") as mock_get:
        mock_dev = MagicMock()
        mock_dev.status.return_value = {"dps": {"1": 235, "2": 48, "4": 92}}
        mock_get.return_value = mock_dev
        result = TuyaDriver().get_status(sensor)
    assert result["is_online"] is True
    assert result["estado"] == {"temperature": 23.5, "humidity": 48, "battery": 92}


def test_get_status_reports_offline_on_error_response():
    from drivers.tuya_driver import TuyaDriver
    plug = {"type": "Enchufe", "ip": "192.168.1.40",
            "config": {"dev_id": "x", "local_key": "y"}}
    with patch.object(TuyaDriver, "_get_device") as mock_get:
        mock_dev = MagicMock()
        mock_dev.status.return_value = {"Error": "timeout"}
        mock_get.return_value = mock_dev
        assert TuyaDriver().get_status(plug)["is_online"] is False


@pytest.mark.parametrize("method_name, args, dev_call, dev_call_args", [
    ("color_rgb", (50, 100, 200), "set_colour", (50, 100, 200)),
    ("temperatura_color", (4000,), "set_colourtemp", (342,)),
])
def test_bulb_actions_go_through_with_device(method_name, args, dev_call, dev_call_args):
    from drivers.tuya_driver import TuyaDriver
    with patch.object(TuyaDriver, "_get_device") as mock_get:
        mock_dev = MagicMock()
        mock_dev.status.return_value = {"dps": {"20": True}}
        mock_get.return_value = mock_dev
        result = getattr(TuyaDriver(), method_name)(_bulb(), *args)
    assert result["ok"] is True
    getattr(mock_dev, dev_call).assert_called_once_with(*dev_call_args)


def test_get_status_bulb_parses_brightness_color_temp_and_hsv():
    from drivers.tuya_driver import TuyaDriver
    with patch.object(TuyaDriver, "_get_device") as mock_get:
        mock_dev = MagicMock()
        mock_dev.status.return_value = {"dps": {
            "20": True, "21": "colour", "22": 500, "23": 500,
            "24": "00780383ff03e8",
        }}
        mock_get.return_value = mock_dev
        estado = TuyaDriver().get_status(_bulb())["estado"]
    assert estado["brightness"] == 50 and estado["work_mode"] == "colour"
    assert estado["color_temp"] == 4600 and estado["color_hex"].startswith("#")


def test_with_device_returns_unreachable_when_status_has_error():
    from drivers.tuya_driver import TuyaDriver
    with patch.object(TuyaDriver, "_get_device") as mock_get:
        mock_dev = MagicMock()
        mock_dev.status.return_value = {"Error": "timeout"}
        mock_get.return_value = mock_dev
        result = TuyaDriver().encender(_bulb())
    assert result["ok"] is False and "bombilla" in result["error"].lower()
