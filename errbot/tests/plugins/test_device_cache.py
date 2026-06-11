from plugins.device_cache import DeviceStateCache


class TestDeviceCache:

    def test_update_and_get_device_state(self):
        cache = DeviceStateCache()
        state = cache.update("device_lampara", state={"power": "on"}, is_online=True)
        assert state.state == {"power": "on"} and state.is_online is True
        assert state.last_update > 0
        cache.update("device_lampara", state={"power": "off"}, is_online=True)
        assert cache.get("device_lampara").state == {"power": "off"}

    def test_mark_offline(self):
        cache = DeviceStateCache()
        cache.update("device_lampara", state={"power": "on"}, is_online=True)
        cache.mark_offline("device_lampara")
        state = cache.get("device_lampara")
        assert state.is_online is False and state.state == {"power": "on"}

        cache.mark_offline("no-exist")
        assert cache.get("no-exist") is None
