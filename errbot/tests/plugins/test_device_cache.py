def test_get_returns_none_for_missing_device():
    from plugins.device_cache import DeviceStateCache
    assert DeviceStateCache().get("nope") is None


def test_update_stores_state_and_get_returns_it_overwriting():
    from plugins.device_cache import DeviceStateCache
    cache = DeviceStateCache()
    state = cache.update("d1", estado={"power": "on"}, is_online=True)
    assert state.estado == {"power": "on"} and state.is_online is True
    assert state.last_update > 0
    cache.update("d1", estado={"power": "off"}, is_online=True)
    assert cache.get("d1").estado == {"power": "off"}


def test_mark_offline_preserves_estado_and_no_ops_on_missing():
    from plugins.device_cache import DeviceStateCache
    cache = DeviceStateCache()
    cache.update("d1", estado={"power": "on"}, is_online=True)
    cache.mark_offline("d1")
    state = cache.get("d1")
    assert state.is_online is False and state.estado == {"power": "on"}

    cache.mark_offline("no-exist")
    assert cache.get("no-exist") is None
