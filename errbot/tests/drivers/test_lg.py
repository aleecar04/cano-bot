import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _device(ip="192.168.1.50", mac="aa:bb:cc:dd:ee:ff", client_key=None):
    return {
        "id": "tv1", "type": "SmartTV", "ip": ip, "mac": mac,
        "config": {"client_key": client_key} if client_key else {},
    }


def _client_mock(**methods):
    client = AsyncMock()
    for name, value in methods.items():
        setattr(client, name, AsyncMock(return_value=value))
    client.disconnect = AsyncMock()
    return client


def _patch_client(client):
    from drivers.lg_tv import LGTVDriver
    return patch.object(LGTVDriver, "_client", AsyncMock(return_value=client))


@pytest.mark.parametrize("power_state, is_online, expected_power", [
    ("Active", True, "on"),
    ("Standby", False, "off"),
])
def test_get_status_maps_power_states(power_state, is_online, expected_power):
    from drivers.lg_tv import LGTVDriver
    with _patch_client(_client_mock(get_power_state={"state": power_state})):
        result = LGTVDriver().get_status(_device())
    assert result["is_online"] is is_online
    assert result["estado"]["power"] == expected_power


def test_get_status_returns_offline_on_client_failure():
    from drivers.lg_tv import LGTVDriver
    with patch.object(LGTVDriver, "_client", AsyncMock(side_effect=RuntimeError("net"))):
        assert LGTVDriver().get_status(_device())["is_online"] is False


def test_encender_uses_wol_with_device_mac():
    from drivers.lg_tv import LGTVDriver
    with patch("drivers.lg_tv.send_magic_packet") as mock_wol:
        assert LGTVDriver().encender(_device()) == {"ok": True}
    mock_wol.assert_called_once_with("aa:bb:cc:dd:ee:ff")


def test_apagar_calls_power_off_and_disconnects():
    from drivers.lg_tv import LGTVDriver
    c = _client_mock(power_off=None)
    with _patch_client(c):
        assert LGTVDriver().apagar(_device()) == {"ok": True}
    c.power_off.assert_awaited_once()
    c.disconnect.assert_awaited_once()


@pytest.mark.parametrize("input_value, expected_volume", [
    (60, 60),
    (200, 100),
])
def test_set_volumen_applies_value_clamped_between_0_and_100(input_value, expected_volume):
    from drivers.lg_tv import LGTVDriver
    c = _client_mock(set_volume=None)
    with _patch_client(c):
        LGTVDriver().set_volumen(_device(), input_value)
    c.set_volume.assert_awaited_with(expected_volume)


@pytest.mark.parametrize("app_name, expected_id", [
    ("youtube", "youtube.leanback.v4"),
    ("miapp", "miapp"),
])
def test_abrir_app_maps_aliases_or_passes_through(app_name, expected_id):
    from drivers.lg_tv import LGTVDriver
    c = _client_mock(launch_app=None)
    with _patch_client(c):
        LGTVDriver().abrir_app(_device(), app_name)
    c.launch_app.assert_awaited_with(expected_id)


@pytest.mark.parametrize("action, payload, expected_method, expected_arg", [
    ("subir_volumen", {}, "_volumen", "up"),
    ("set_volumen", {"valor": 30}, "set_volumen", 30),
    ("abrir_app", {"app": "netflix"}, "abrir_app", "netflix"),
])
def test_ejecutar_dispatches_to_the_right_method(action, payload, expected_method, expected_arg):
    from drivers.lg_tv import LGTVDriver
    drv = LGTVDriver()
    with patch.object(drv, expected_method, return_value={"ok": True}) as mock_method:
        drv.ejecutar(_device(), action, payload)
    assert mock_method.call_args[0][1] == expected_arg


class TestClientKeyPersistence:

    def test_keeps_existing_key_when_unchanged(self):
        from drivers.lg_tv import LGTVDriver
        import drivers.lg_tv as lg

        client = MagicMock(); client.client_key = "k"; client.connect = AsyncMock()
        with patch.object(lg, "WebOsClient", return_value=client), \
             patch.object(lg.api_devices, "patch_config") as mock_patch:
            asyncio.run(LGTVDriver()._client(_device(client_key="k")))
        mock_patch.assert_not_called()

    def test_persists_new_key_via_api_devices(self):
        from drivers.lg_tv import LGTVDriver
        import drivers.lg_tv as lg

        client = MagicMock(); client.client_key = "key-nueva"; client.connect = AsyncMock()
        with patch.object(lg, "WebOsClient", return_value=client), \
             patch.object(lg.api_devices, "patch_config") as mock_patch, \
             patch.object(lg.asyncio, "to_thread",
                          side_effect=lambda f, *a, **k: mock_patch(*a, **k)):
            result = asyncio.run(LGTVDriver()._client(_device(client_key="key-vieja")))
        assert result is client
        mock_patch.assert_called_once()


def test_encender_returns_error_when_device_has_no_mac():
    from drivers.lg_tv import LGTVDriver
    result = LGTVDriver().encender(_device(mac=None))
    assert result["ok"] is False and "MAC" in result["error"]


def test_ejecutar_falls_back_to_super_for_unknown_action():
    from drivers.lg_tv import LGTVDriver
    drv = LGTVDriver()
    with patch("drivers.base.BaseDriver.ejecutar", return_value={"ok": True, "default": True}) as mock_super:
        drv.ejecutar(_device(), "accion_desconocida", {})
    mock_super.assert_called_once()


@pytest.mark.parametrize("action, expected_call", [("subir_volumen", "volume_up"), ("bajar_volumen", "volume_down")])
def test_volumen_up_and_down(action, expected_call):
    from drivers.lg_tv import LGTVDriver
    c = _client_mock(volume_up=None, volume_down=None)
    with _patch_client(c):
        LGTVDriver().ejecutar(_device(), action, {})
    getattr(c, expected_call).assert_awaited_once()


def test_mute_calls_set_mute():
    from drivers.lg_tv import LGTVDriver
    c = _client_mock(set_mute=None)
    with _patch_client(c):
        LGTVDriver().ejecutar(_device(), "mute", {})
    c.set_mute.assert_awaited_once()
