from unittest.mock import MagicMock, patch


def _device(ip="192.168.1.20", mac="aa:bb:cc:dd:ee:ff", token=None):
    return {
        "id": "s1", "type": "SmartTV", "ip": ip, "mac": mac,
        "config": {"token": token} if token else {},
    }


# ── _tv (factoría) ───────────────────────────────────────────────────────────

class TestTvFactory:

    def test_lanza_si_lib_no_disponible(self):
        from drivers.samsung_tv import SamsungTVDriver
        with patch("drivers.samsung_tv.SAMSUNG_AVAILABLE", False):
            try:
                SamsungTVDriver()._tv(_device())
            except RuntimeError as e:
                assert "samsungtvws" in str(e)
            else:
                raise AssertionError("se esperaba RuntimeError")

    def test_construye_samsungtvws_con_ip_y_token(self):
        from drivers.samsung_tv import SamsungTVDriver
        with patch("drivers.samsung_tv.SAMSUNG_AVAILABLE", True), \
             patch("drivers.samsung_tv.SamsungTVWS") as mock_cls:
            SamsungTVDriver()._tv(_device(token="tk1"))
        mock_cls.assert_called_once()
        kwargs = mock_cls.call_args.kwargs
        assert kwargs["host"] == "192.168.1.20"
        assert kwargs["token"] == "tk1"


# ── _send_key ────────────────────────────────────────────────────────────────

class TestSendKey:

    def test_envia_la_tecla(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        with patch.object(drv, "_tv", return_value=tv):
            result = drv._send_key(_device(), "KEY_POWER")
        assert result == {"ok": True}
        tv.send_key.assert_called_once_with("KEY_POWER")

    def test_excepcion_devuelve_error(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        with patch.object(drv, "_tv", side_effect=RuntimeError("net")):
            result = drv._send_key(_device(), "KEY_POWER")
        assert result["ok"] is False
        assert "net" in result["error"]


# ── get_status ───────────────────────────────────────────────────────────────

class TestGetStatus:

    def test_status_power_on(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        tv.rest_device_info.return_value = {"device": {"PowerState": "on"}}
        with patch.object(drv, "_tv", return_value=tv):
            result = drv.get_status(_device())
        assert result["is_online"] is True
        assert result["estado"]["power"] == "on"

    def test_status_power_off(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        tv.rest_device_info.return_value = {"device": {"PowerState": "standby"}}
        with patch.object(drv, "_tv", return_value=tv):
            result = drv.get_status(_device())
        assert result["estado"]["power"] == "off"

    def test_status_excepcion_devuelve_offline(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        with patch.object(drv, "_tv", side_effect=RuntimeError("boom")):
            result = drv.get_status(_device())
        assert result["is_online"] is False


# ── encender / apagar ────────────────────────────────────────────────────────

class TestEncenderApagar:

    def test_encender_envia_magic_packet(self):
        from drivers.samsung_tv import SamsungTVDriver
        with patch("drivers.samsung_tv.send_magic_packet") as mock_wol:
            result = SamsungTVDriver().encender(_device())
        assert result == {"ok": True}
        mock_wol.assert_called_once_with("aa:bb:cc:dd:ee:ff")

    def test_encender_sin_mac_devuelve_error(self):
        from drivers.samsung_tv import SamsungTVDriver
        dev = _device(mac=None)
        result = SamsungTVDriver().encender(dev)
        assert result["ok"] is False

    def test_encender_excepcion_devuelve_error(self):
        from drivers.samsung_tv import SamsungTVDriver
        with patch("drivers.samsung_tv.send_magic_packet", side_effect=OSError("no socket")):
            result = SamsungTVDriver().encender(_device())
        assert result["ok"] is False

    def test_apagar_envia_key_power(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        with patch.object(drv, "_tv", return_value=tv):
            drv.apagar(_device())
        tv.send_key.assert_called_once_with("KEY_POWER")


# ── set_volumen ──────────────────────────────────────────────────────────────

class TestSetVolumen:

    def test_sube_si_target_mayor(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        tv.rest_device_info.return_value = {"device": {"Volume": 20}}
        with patch.object(drv, "_tv", return_value=tv):
            drv.set_volumen(_device(), 25)
        # Step de 20 → 25 = 5 pulsaciones de VOLUMEUP
        assert tv.send_key.call_count == 5
        assert tv.send_key.call_args_list[0][0][0] == "KEY_VOLUMEUP"

    def test_baja_si_target_menor(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        tv.rest_device_info.return_value = {"device": {"Volume": 30}}
        with patch.object(drv, "_tv", return_value=tv):
            drv.set_volumen(_device(), 27)
        assert tv.send_key.call_count == 3
        assert tv.send_key.call_args_list[0][0][0] == "KEY_VOLUMEDOWN"

    def test_clampa_a_0_100(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        tv.rest_device_info.return_value = {"device": {"Volume": 50}}
        with patch.object(drv, "_tv", return_value=tv):
            drv.set_volumen(_device(), 200)  # target capped a 100
        assert tv.send_key.call_count == 50

    def test_excepcion_devuelve_error(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        with patch.object(drv, "_tv", side_effect=RuntimeError("boom")):
            result = drv.set_volumen(_device(), 30)
        assert result["ok"] is False


# ── abrir_app ────────────────────────────────────────────────────────────────

class TestAbrirApp:

    def test_netflix_usa_key_directa(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        with patch.object(drv, "_tv", return_value=tv):
            drv.abrir_app(_device(), "netflix")
        tv.send_key.assert_called_once_with("KEY_NETFLIX")

    def test_otra_app_lanza_run_app(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        with patch.object(drv, "_tv", return_value=tv):
            drv.abrir_app(_device(), "youtube")
        tv.run_app.assert_called_once()

    def test_app_desconocida_pasa_string_tal_cual(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        with patch.object(drv, "_tv", return_value=tv):
            drv.abrir_app(_device(), "extranjera")
        tv.run_app.assert_called_once_with("extranjera")

    def test_run_app_excepcion_devuelve_error(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        tv.run_app.side_effect = RuntimeError("net")
        with patch.object(drv, "_tv", return_value=tv):
            result = drv.abrir_app(_device(), "youtube")
        assert result["ok"] is False


# ── ejecutar (dispatcher con extras de TV) ───────────────────────────────────

class TestEjecutar:

    def test_subir_volumen_envia_key(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        with patch.object(drv, "_tv", return_value=tv):
            drv.ejecutar(_device(), "subir_volumen", {})
        tv.send_key.assert_called_once_with("KEY_VOLUMEUP")

    def test_bajar_volumen_envia_key(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        with patch.object(drv, "_tv", return_value=tv):
            drv.ejecutar(_device(), "bajar_volumen", {})
        tv.send_key.assert_called_once_with("KEY_VOLUMEDOWN")

    def test_mute_envia_key(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        tv = MagicMock()
        with patch.object(drv, "_tv", return_value=tv):
            drv.ejecutar(_device(), "mute", {})
        tv.send_key.assert_called_once_with("KEY_MUTE")

    def test_abrir_app_via_dispatcher(self):
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        with patch.object(drv, "abrir_app") as mock_app:
            drv.ejecutar(_device(), "abrir_app", {"app": "netflix"})
        mock_app.assert_called_once()

    def test_accion_no_extra_cae_a_super(self):
        """Acciones core (encender/apagar) caen al dispatcher base."""
        from drivers.samsung_tv import SamsungTVDriver
        drv = SamsungTVDriver()
        with patch.object(drv, "encender", return_value={"ok": True}) as mock_e:
            drv.ejecutar(_device(), "encender", {})
        mock_e.assert_called_once()
