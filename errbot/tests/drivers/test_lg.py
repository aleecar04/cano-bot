from unittest.mock import AsyncMock, MagicMock, patch


def _device(ip="192.168.1.50", mac="aa:bb:cc:dd:ee:ff", client_key=None):
    return {
        "id": "tv1", "type": "SmartTV", "ip": ip, "mac": mac,
        "config": {"client_key": client_key} if client_key else {},
    }


def _client_mock(**methods):
    """Crea un mock del cliente async con los métodos pasados."""
    client = AsyncMock()
    for name, value in methods.items():
        setattr(client, name, AsyncMock(return_value=value))
    client.disconnect = AsyncMock()
    return client


def _patch_client(client):
    """Patchea LGTVDriver._client para que devuelva el mock."""
    from drivers.lg_tv import LGTVDriver
    return patch.object(LGTVDriver, "_client", AsyncMock(return_value=client))


# ── get_status ───────────────────────────────────────────────────────────────

class TestGetStatus:

    def test_active_devuelve_online_on(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(get_power_state={"state": "Active"})
        with _patch_client(c):
            result = LGTVDriver().get_status(_device())
        assert result["is_online"] is True
        assert result["estado"]["power"] == "on"

    def test_screen_on_devuelve_online(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(get_power_state={"state": "Screen On"})
        with _patch_client(c):
            result = LGTVDriver().get_status(_device())
        assert result["is_online"] is True

    def test_estado_desconocido_devuelve_offline(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(get_power_state={"state": "Standby"})
        with _patch_client(c):
            result = LGTVDriver().get_status(_device())
        assert result["is_online"] is False
        assert result["estado"]["power"] == "off"

    def test_excepcion_en_client_devuelve_offline(self):
        from drivers.lg_tv import LGTVDriver
        with patch.object(LGTVDriver, "_client",
                          AsyncMock(side_effect=RuntimeError("net"))):
            result = LGTVDriver().get_status(_device())
        assert result["is_online"] is False

    def test_run_devuelve_error_propaga_offline(self):
        """Cuando _run captura una excepción devuelve {ok: False, error: ...}; get_status
        lo traduce a is_online=False."""
        from drivers.lg_tv import LGTVDriver
        drv = LGTVDriver()
        with patch.object(drv, "_run", return_value={"ok": False, "error": "boom"}):
            result = drv.get_status(_device())
        assert result["is_online"] is False
        assert result["error"] == "boom"


# ── encender (Wake on LAN) ───────────────────────────────────────────────────

class TestEncender:

    def test_envia_magic_packet_con_mac(self):
        from drivers.lg_tv import LGTVDriver
        with patch("drivers.lg_tv.send_magic_packet") as mock_wol:
            result = LGTVDriver().encender(_device())
        assert result == {"ok": True}
        mock_wol.assert_called_once_with("aa:bb:cc:dd:ee:ff")

    def test_sin_mac_devuelve_error(self):
        from drivers.lg_tv import LGTVDriver
        result = LGTVDriver().encender(_device(mac=None))
        assert result["ok"] is False
        assert "MAC" in result["error"]

    def test_excepcion_devuelve_error(self):
        from drivers.lg_tv import LGTVDriver
        with patch("drivers.lg_tv.send_magic_packet", side_effect=OSError("no socket")):
            result = LGTVDriver().encender(_device())
        assert result["ok"] is False


# ── apagar ───────────────────────────────────────────────────────────────────

class TestApagar:

    def test_llama_power_off_y_disconnect(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(power_off=None)
        with _patch_client(c):
            result = LGTVDriver().apagar(_device())
        assert result == {"ok": True}
        c.power_off.assert_awaited_once()
        c.disconnect.assert_awaited_once()


# ── set_volumen ──────────────────────────────────────────────────────────────

class TestSetVolumen:

    def test_aplica_volumen_y_devuelve_ok(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(set_volume=None)
        with _patch_client(c):
            result = LGTVDriver().set_volumen(_device(), 60)
        assert result == {"ok": True, "volumen": 60}
        c.set_volume.assert_awaited_once_with(60)

    def test_clampa_a_0_100(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(set_volume=None)
        with _patch_client(c):
            LGTVDriver().set_volumen(_device(), 200)
        c.set_volume.assert_awaited_once_with(100)

    def test_clampa_a_0_si_negativo(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(set_volume=None)
        with _patch_client(c):
            LGTVDriver().set_volumen(_device(), -5)
        c.set_volume.assert_awaited_once_with(0)


# ── abrir_app ────────────────────────────────────────────────────────────────

class TestAbrirApp:

    def test_netflix_se_mapea_via_LG_APPS(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(launch_app=None)
        with _patch_client(c):
            result = LGTVDriver().abrir_app(_device(), "netflix")
        assert result == {"ok": True, "app": "netflix"}
        c.launch_app.assert_awaited_once_with("netflix")

    def test_youtube_se_mapea_via_LG_APPS(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(launch_app=None)
        with _patch_client(c):
            LGTVDriver().abrir_app(_device(), "youtube")
        c.launch_app.assert_awaited_once_with("youtube.leanback.v4")

    def test_app_desconocida_pasa_tal_cual(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(launch_app=None)
        with _patch_client(c):
            LGTVDriver().abrir_app(_device(), "miapp")
        c.launch_app.assert_awaited_once_with("miapp")

    def test_es_case_insensitive(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(launch_app=None)
        with _patch_client(c):
            LGTVDriver().abrir_app(_device(), "NETFLIX")
        c.launch_app.assert_awaited_once_with("netflix")


# ── _volumen / _mute ─────────────────────────────────────────────────────────

class TestVolumenStep:

    def test_up_llama_volume_up(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(volume_up=None, volume_down=None)
        with _patch_client(c):
            LGTVDriver()._volumen(_device(), "up")
        c.volume_up.assert_awaited_once()
        c.volume_down.assert_not_awaited()

    def test_down_llama_volume_down(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(volume_up=None, volume_down=None)
        with _patch_client(c):
            LGTVDriver()._volumen(_device(), "down")
        c.volume_down.assert_awaited_once()
        c.volume_up.assert_not_awaited()


class TestMute:

    def test_mute_toggle_false_a_true(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(get_volume={"muted": False}, set_mute=None)
        with _patch_client(c):
            LGTVDriver()._mute(_device())
        c.set_mute.assert_awaited_once_with(True)

    def test_mute_toggle_true_a_false(self):
        from drivers.lg_tv import LGTVDriver
        c = _client_mock(get_volume={"muted": True}, set_mute=None)
        with _patch_client(c):
            LGTVDriver()._mute(_device())
        c.set_mute.assert_awaited_once_with(False)


# ── ejecutar (dispatcher con extras) ─────────────────────────────────────────

class TestEjecutar:

    def test_subir_volumen_va_a_volumen_up(self):
        from drivers.lg_tv import LGTVDriver
        drv = LGTVDriver()
        with patch.object(drv, "_volumen", return_value={"ok": True}) as mock_v:
            drv.ejecutar(_device(), "subir_volumen", {})
        mock_v.assert_called_once_with(_device(), "up")

    def test_bajar_volumen_va_a_volumen_down(self):
        from drivers.lg_tv import LGTVDriver
        drv = LGTVDriver()
        with patch.object(drv, "_volumen", return_value={"ok": True}) as mock_v:
            drv.ejecutar(_device(), "bajar_volumen", {})
        mock_v.assert_called_once_with(_device(), "down")

    def test_mute_va_a_mute(self):
        from drivers.lg_tv import LGTVDriver
        drv = LGTVDriver()
        with patch.object(drv, "_mute", return_value={"ok": True}) as mock_m:
            drv.ejecutar(_device(), "mute", {})
        mock_m.assert_called_once()

    def test_set_volumen_pasa_valor(self):
        from drivers.lg_tv import LGTVDriver
        drv = LGTVDriver()
        with patch.object(drv, "set_volumen", return_value={"ok": True}) as mock_sv:
            drv.ejecutar(_device(), "set_volumen", {"valor": 30})
        mock_sv.assert_called_once_with(_device(), 30)

    def test_abrir_app_pasa_nombre(self):
        from drivers.lg_tv import LGTVDriver
        drv = LGTVDriver()
        with patch.object(drv, "abrir_app", return_value={"ok": True}) as mock_a:
            drv.ejecutar(_device(), "abrir_app", {"app": "netflix"})
        mock_a.assert_called_once_with(_device(), "netflix")

    def test_accion_core_delega_a_super(self):
        from drivers.lg_tv import LGTVDriver
        drv = LGTVDriver()
        with patch.object(drv, "encender", return_value={"ok": True}) as mock_e:
            drv.ejecutar(_device(), "encender", {})
        mock_e.assert_called_once()


# ── _client guarda nueva client_key si la recibe del TV ──────────────────────

class TestClientKeyPersistence:

    def test_guarda_si_cambia(self):
        """Si la TV nos devuelve un client_key nuevo, _client lo persiste vía api_devices.patch_config."""
        from drivers.lg_tv import LGTVDriver
        client = MagicMock()
        client.client_key = "key-nueva"
        client.connect = AsyncMock()
        import drivers.lg_tv as lg
        with patch.object(lg, "WebOsClient", return_value=client), \
             patch.object(lg.api_devices, "patch_config") as mock_patch, \
             patch.object(lg.asyncio, "to_thread",
                          side_effect=lambda f, *a, **k: mock_patch(*a, **k)):
            import asyncio as _aio
            result = _aio.run(LGTVDriver()._client(_device(client_key="key-vieja")))
        assert result is client
        mock_patch.assert_called_once()

    def test_no_guarda_si_misma_key(self):
        from drivers.lg_tv import LGTVDriver
        client = MagicMock()
        client.client_key = "k"
        client.connect = AsyncMock()
        import drivers.lg_tv as lg
        with patch.object(lg, "WebOsClient", return_value=client), \
             patch.object(lg.api_devices, "patch_config") as mock_patch:
            import asyncio as _aio
            _aio.run(LGTVDriver()._client(_device(client_key="k")))
        mock_patch.assert_not_called()

    def test_patch_config_falla_silenciosamente(self):
        from drivers.lg_tv import LGTVDriver
        client = MagicMock()
        client.client_key = "key-nueva"
        client.connect = AsyncMock()
        import drivers.lg_tv as lg
        with patch.object(lg, "WebOsClient", return_value=client), \
             patch.object(lg.asyncio, "to_thread",
                          side_effect=RuntimeError("boom")):
            import asyncio as _aio
            # No debe lanzar
            _aio.run(LGTVDriver()._client(_device(client_key="key-vieja")))
