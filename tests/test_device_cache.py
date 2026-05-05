"""Tests for plugins/device_cache.py — DeviceStateCache."""

import time
import pytest
from plugins.device_cache import DeviceStateCache, DeviceState


@pytest.fixture
def cache():
    return DeviceStateCache()


def test_device_state_is_stale_when_old():
    state = DeviceState(
        device_id="d1",
        estado={},
        is_online=True,
        last_update=time.time() - 120,  # 2 min ago
        source="poll",
    )
    assert state.is_stale(timeout=60) is True


def test_device_state_not_stale_when_recent():
    state = DeviceState(
        device_id="d1",
        estado={},
        is_online=True,
        last_update=time.time() - 10,
        source="poll",
    )
    assert state.is_stale(timeout=60) is False


def test_device_state_age_seconds():
    state = DeviceState(
        device_id="d1",
        estado={},
        is_online=True,
        last_update=time.time() - 30,
        source="poll",
    )
    assert 28 <= state.age_seconds() <= 32


def test_device_state_to_dict_contains_extra_fields():
    state = DeviceState(
        device_id="d1",
        estado={"power": "on"},
        is_online=True,
        last_update=time.time(),
        source="action",
    )
    d = state.to_dict()
    assert "last_update_iso" in d
    assert "age_seconds" in d


def test_update_and_get(cache):
    state = cache.update("dev-1", {"power": "on"}, is_online=True, source="poll")

    assert state.device_id == "dev-1"
    assert state.is_online is True
    assert state.estado == {"power": "on"}

    retrieved = cache.get("dev-1")
    assert retrieved is state


def test_get_missing_returns_none(cache):
    assert cache.get("nonexistent") is None


def test_update_overwrites_previous(cache):
    cache.update("dev-1", {"power": "on"}, is_online=True)
    cache.update("dev-1", {"power": "off"}, is_online=False)

    state = cache.get("dev-1")
    assert state.estado == {"power": "off"}
    assert state.is_online is False


def test_get_all_returns_copy(cache):
    cache.update("a", {}, is_online=True)
    cache.update("b", {}, is_online=False)

    all_devices = cache.get_all()
    assert set(all_devices.keys()) == {"a", "b"}

    # Modifying the returned dict must not affect the cache
    del all_devices["a"]
    assert cache.get("a") is not None


def test_mark_offline_sets_is_online_false(cache):
    cache.update("dev-1", {"power": "on"}, is_online=True)
    cache.mark_offline("dev-1")

    assert cache.get("dev-1").is_online is False


def test_mark_offline_lowers_confidence(cache):
    cache.update("dev-1", {}, is_online=True, confidence=1.0)
    cache.mark_offline("dev-1")

    assert cache.get("dev-1").confidence < 1.0


def test_mark_helpers_on_missing_device_do_not_raise(cache):
    cache.mark_offline("ghost")


def test_clear_single_device(cache):
    cache.update("a", {}, is_online=True)
    cache.update("b", {}, is_online=True)
    cache.clear("a")

    assert cache.get("a") is None
    assert cache.get("b") is not None


def test_clear_all(cache):
    cache.update("a", {}, is_online=True)
    cache.update("b", {}, is_online=True)
    cache.clear()

    assert cache.get_all() == {}


def test_get_stale_devices_filters_correctly(cache):
    cache.update("fresh", {}, is_online=True)

    # Manually create a stale entry
    stale = DeviceState("stale", {}, True, time.time() - 120, "poll")
    cache.devices["stale"] = stale

    stale_map = cache.get_stale_devices(timeout=60)
    assert "stale" in stale_map
    assert "fresh" not in stale_map


def test_status_summary_counts(cache):
    cache.update("a", {}, is_online=True)
    cache.update("b", {}, is_online=True)
    cache.update("c", {}, is_online=False)

    summary = cache.get_status_summary()
    assert summary["total_cached"] == 3
    assert summary["online"] == 2
    assert summary["offline"] == 1


def test_status_summary_empty_cache(cache):
    summary = cache.get_status_summary()
    assert summary["total_cached"] == 0
    assert summary["last_update"] == 0
