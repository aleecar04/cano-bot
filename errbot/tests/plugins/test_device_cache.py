

class TestDeviceStateCache:

    def test_get_devuelve_none_si_no_existe(self):
        from plugins.device_cache import DeviceStateCache
        cache = DeviceStateCache()
        assert cache.get("nope") is None

    def test_update_guarda_y_devuelve_state(self):
        from plugins.device_cache import DeviceStateCache
        cache = DeviceStateCache()
        state = cache.update("d1", estado={"power": "on"}, is_online=True)
        assert state.estado == {"power": "on"}
        assert state.is_online is True
        assert state.last_update > 0

    def test_get_tras_update_devuelve_state_guardado(self):
        from plugins.device_cache import DeviceStateCache
        cache = DeviceStateCache()
        cache.update("d1", estado={"power": "on"}, is_online=True)
        got = cache.get("d1")
        assert got.estado == {"power": "on"}

    def test_update_sobrescribe(self):
        from plugins.device_cache import DeviceStateCache
        cache = DeviceStateCache()
        cache.update("d1", estado={"power": "on"}, is_online=True)
        cache.update("d1", estado={"power": "off"}, is_online=True)
        assert cache.get("d1").estado == {"power": "off"}

    def test_mark_offline_solo_cambia_is_online(self):
        from plugins.device_cache import DeviceStateCache
        cache = DeviceStateCache()
        cache.update("d1", estado={"power": "on"}, is_online=True)
        cache.mark_offline("d1")
        state = cache.get("d1")
        assert state.is_online is False
        assert state.estado == {"power": "on"}  # estado preservado

    def test_mark_offline_en_device_inexistente_no_lanza(self):
        from plugins.device_cache import DeviceStateCache
        cache = DeviceStateCache()
        cache.mark_offline("no-exist")  # no lanza
        assert cache.get("no-exist") is None
