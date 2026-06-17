import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import drivers.lg_tv as lg
from drivers.lg_tv import LGTVDriver


def _device(ip="192.168.1.50", mac="aa:bb:cc:dd:ee:ff", client_key=None):
    return {
        "id": "device_lampara", "type": "SmartTV", "ip": ip, "mac": mac,
        "config": {"client_key": client_key} if client_key else {},
    }


def _client_mock(**methods):
    client = AsyncMock()
    for name, value in methods.items():
        setattr(client, name, AsyncMock(return_value=value))
    client.disconnect = AsyncMock()
    return client


def _patch_client(client):
    return patch.object(LGTVDriver, "_client", AsyncMock(return_value=client))


class TestLGTVDriver:

    @pytest.mark.parametrize("power_state, is_online, expected_power", [
        ("Active", True, "on"),
        ("Standby", False, "off"),
    ])
    def test_get_status_maps_power_states(self, power_state, is_online, expected_power):
        with _patch_client(_client_mock(get_power_state={"state": power_state})):
            result = LGTVDriver().get_status(_device())
        assert result["is_online"] is is_online
        assert result["state"]["power"] == expected_power

    def test_get_status_returns_offline_on_error(self):
        with patch.object(LGTVDriver, "_client", AsyncMock(side_effect=RuntimeError("net"))):
            assert LGTVDriver().get_status(_device())["is_online"] is False

    def test_set_volume_returns_real_volume_from_tv(self):
        client = _client_mock(set_volume=None, get_volume={"volume": 42})
        with _patch_client(client):
            result = LGTVDriver().set_volume(_device(), 50)
        assert result["ok"] is True
        # devuelve el volumen REAL leído (42), no el pedido (50)
        assert result["state"]["volume"] == 42

    def test_volume_step_returns_real_volume_from_tv(self):
        client = _client_mock(volume_up=None, get_volume={"volume": 11})
        with _patch_client(client):
            result = LGTVDriver()._volume_step(_device(), "up")
        assert result["ok"] is True
        assert result["state"]["volume"] == 11

    def test_turn_on_uses_wol(self):
        with patch("drivers.lg_tv.send_magic_packet") as mock_wol:
            assert LGTVDriver().turn_on(_device()) == {"ok": True}
        mock_wol.assert_called_once_with("aa:bb:cc:dd:ee:ff")

    def test_turn_off_calls_power_off_and_disconnects(self):
        c = _client_mock(power_off=None)
        with _patch_client(c):
            assert LGTVDriver().turn_off(_device()) == {"ok": True}
        c.power_off.assert_awaited_once()
        c.disconnect.assert_awaited_once()

    @pytest.mark.parametrize("action, payload, expected_volume", [
        ("set_volumen", {"value": 200}, 100),
        ("mute",        {},             0),
    ])
    def test_volume_and_mute_end_at_set_volume(self, action, payload, expected_volume):
        c = _client_mock(set_volume=None)
        with _patch_client(c):
            LGTVDriver().execute(_device(), action, payload)
        c.set_volume.assert_awaited_with(expected_volume)

    def test_open_app_maps_aliases_or_passes_through(self):
        c = _client_mock(launch_app=None)
        with _patch_client(c):
            LGTVDriver().open_app(_device(), "youtube")
        c.launch_app.assert_awaited_with("youtube.leanback.v4")

    def test_turn_on_returns_error_without_mac(self):
        result = LGTVDriver().turn_on(_device(mac=None))
        assert result["ok"] is False and "MAC" in result["error"]
