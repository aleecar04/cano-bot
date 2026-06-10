from unittest.mock import MagicMock, patch

import pytest


def _device(ip="192.168.1.20", mac="aa:bb:cc:dd:ee:ff", token=None):
    return {
        "id": "s1", "type": "SmartTV", "ip": ip, "mac": mac,
        "config": {"token": token} if token else {},
    }


def test_tv_factory_requires_library():
    from drivers.samsung_tv import SamsungTVDriver
    with patch("drivers.samsung_tv.SAMSUNG_AVAILABLE", False):
        with pytest.raises(RuntimeError, match="samsungtvws"):
            SamsungTVDriver()._tv(_device())


def test_tv_factory_passes_ip_and_token():
    from drivers.samsung_tv import SamsungTVDriver
    with patch("drivers.samsung_tv.SAMSUNG_AVAILABLE", True), \
         patch("drivers.samsung_tv.SamsungTVWS") as mock_cls:
        SamsungTVDriver()._tv(_device(token="tk1"))
    kwargs = mock_cls.call_args.kwargs
    assert kwargs["host"] == "192.168.1.20" and kwargs["token"] == "tk1"


def test_get_status_returns_offline_on_exception():
    from drivers.samsung_tv import SamsungTVDriver
    drv = SamsungTVDriver()
    with patch.object(drv, "_tv", side_effect=RuntimeError("boom")):
        assert drv.get_status(_device())["is_online"] is False


@pytest.mark.parametrize("power_state, expected_power", [
    ("on", "on"),
    ("standby", "off"),
])
def test_get_status_maps_power_state(power_state, expected_power):
    from drivers.samsung_tv import SamsungTVDriver
    drv = SamsungTVDriver()
    tv = MagicMock()
    tv.rest_device_info.return_value = {"device": {"PowerState": power_state}}
    with patch.object(drv, "_tv", return_value=tv):
        assert drv.get_status(_device())["estado"]["power"] == expected_power


def test_encender_uses_wol_with_mac():
    from drivers.samsung_tv import SamsungTVDriver
    with patch("drivers.samsung_tv.send_magic_packet") as mock_wol:
        assert SamsungTVDriver().encender(_device()) == {"ok": True}
    mock_wol.assert_called_once_with("aa:bb:cc:dd:ee:ff")


def test_set_volumen_presses_volume_up_until_target():
    from drivers.samsung_tv import SamsungTVDriver
    drv = SamsungTVDriver()
    tv = MagicMock()
    tv.rest_device_info.return_value = {"device": {"Volume": 20}}
    with patch.object(drv, "_tv", return_value=tv):
        drv.set_volumen(_device(), 25)
    assert tv.send_key.call_count == 5
    assert tv.send_key.call_args_list[0][0][0] == "KEY_VOLUMEUP"


def test_abrir_app_uses_direct_key_for_known_apps():
    from drivers.samsung_tv import SamsungTVDriver
    drv = SamsungTVDriver()
    tv = MagicMock()
    with patch.object(drv, "_tv", return_value=tv):
        drv.abrir_app(_device(), "netflix")
    tv.send_key.assert_called_once_with("KEY_NETFLIX")


def test_abrir_app_runs_app_by_name_when_no_key_available():
    from drivers.samsung_tv import SamsungTVDriver
    drv = SamsungTVDriver()
    tv = MagicMock()
    with patch.object(drv, "_tv", return_value=tv):
        drv.abrir_app(_device(), "youtube")
    tv.run_app.assert_called_once()


@pytest.mark.parametrize("action, expected_key", [
    ("subir_volumen", "KEY_VOLUMEUP"),
    ("mute", "KEY_MUTE"),
])
def test_ejecutar_volume_and_mute_send_corresponding_key(action, expected_key):
    from drivers.samsung_tv import SamsungTVDriver
    drv = SamsungTVDriver()
    tv = MagicMock()
    with patch.object(drv, "_tv", return_value=tv):
        drv.ejecutar(_device(), action, {})
    tv.send_key.assert_called_once_with(expected_key)


