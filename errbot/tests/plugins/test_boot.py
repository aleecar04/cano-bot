from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest


def _make_boot():
    from plugins.boot.boot import Boot
    b = Boot.__new__(Boot)
    b.devices = []
    b.executor = ThreadPoolExecutor(max_workers=2)
    return b


@pytest.mark.parametrize("reachable, api_kwargs, expected", [
    (False, {}, "OLD"),
    (True, {"return_value": [{"id": "new1"}, {"id": "new2"}]}, "NEW"),
    (True, {"side_effect": RuntimeError("boom")}, "OLD"),
])
def test_fetch_devices_or_falls_back_to_cached(reachable, api_kwargs, expected):
    b = _make_boot()
    b.devices = [{"id": "old"}]
    with patch("plugins.boot.boot.is_backend_reachable", return_value=reachable), \
         patch("plugins.boot.boot.api_devices.get_all", **api_kwargs):
        result = b._fetch_devices_from_backend()
    if expected == "OLD":
        assert result == [{"id": "old"}]
    else:
        assert result == api_kwargs["return_value"]


@pytest.mark.parametrize("reachable, patch_kwargs, should_update", [
    (False, {}, False),
    (True, {}, True),
    (True, {"side_effect": RuntimeError("net")}, False),
])
def test_patch_backend_updates_cache_only_on_successful_request(reachable, patch_kwargs, should_update):
    b = _make_boot()
    with patch("plugins.boot.boot.is_backend_reachable", return_value=reachable), \
         patch("plugins.boot.boot.api_devices.patch_status", **patch_kwargs), \
         patch("plugins.boot.boot.device_cache.update") as mock_upd:
        b._patch_backend("d1", True, {"power": "on"})
    assert mock_upd.called is should_update


@pytest.mark.parametrize("cache_state, new_status, should_patch", [
    (MagicMock(is_online=True, estado={"power": "on"}),
     {"is_online": True, "estado": {"power": "on"}}, False),
    (MagicMock(is_online=True, estado={"power": "on"}),
     {"is_online": True, "estado": {"power": "off"}}, True)
])
def test_sync_if_changed_only_patches_on_real_changes(cache_state, new_status, should_patch):
    b = _make_boot()
    with patch("plugins.boot.boot.device_cache.get", return_value=cache_state), \
         patch.object(b, "_patch_backend") as mock_patch:
        b._sync_if_changed("d1", new_status)
    assert mock_patch.called is should_patch


@pytest.mark.parametrize("cached_online, should_patch", [
    (False, False),
    (True, True)
])
def test_sync_offline_only_on_transition(cached_online, should_patch):
    b = _make_boot()
    cached = MagicMock(is_online=cached_online, estado={})
    with patch("plugins.boot.boot.device_cache.get", return_value=cached), \
         patch.object(b, "_patch_backend") as mock_patch:
        b._sync_offline("d1")
    assert mock_patch.called is should_patch
    if should_patch:
        assert mock_patch.call_args.kwargs["is_online"] is False


def test_poll_one_returns_none_for_unknown_driver():
    b = _make_boot()
    assert b._poll_one({"id": "d1", "driver": "noexiste"}) is None


def test_poll_one_marks_offline_when_driver_raises():
    b = _make_boot()
    mock_driver = MagicMock(); mock_driver.get_status.side_effect = RuntimeError("boom")
    with patch.dict("plugins.boot.boot.DRIVERS", {"tuya": mock_driver}), \
         patch.object(b, "_sync_offline") as mock_off:
        assert b._poll_one({"id": "d1", "driver": "tuya", "name": "Luz"}) is None
    mock_off.assert_called_once_with("d1")


def test_poll_one_syncs_status_on_success():
    b = _make_boot()
    status = {"is_online": True, "estado": {"power": "on"}}
    mock_driver = MagicMock(); mock_driver.get_status.return_value = status
    with patch.dict("plugins.boot.boot.DRIVERS", {"tuya": mock_driver}), \
         patch.object(b, "_sync_if_changed") as mock_sync:
        assert b._poll_one({"id": "d1", "driver": "tuya"}) == status
    mock_sync.assert_called_once_with("d1", status)


def test_probe_home_network_returns_false_when_no_gateway():
    b = _make_boot()
    with patch("plugins.boot.boot.netifaces.gateways", return_value={"default": {}}):
        assert b._probe_home_network() is False


@pytest.mark.parametrize("create_connection_side_effect, expected", [
    (None, True),
    (OSError, False),
])
def test_probe_home_network_classifies_socket_outcomes(create_connection_side_effect, expected):
    b = _make_boot()
    gw = {"default": {2: ("192.168.1.1", "eth0")}}
    return_value = MagicMock() if create_connection_side_effect is None else None
    with patch("plugins.boot.boot.netifaces.gateways", return_value=gw), \
         patch("plugins.boot.boot.netifaces.AF_INET", 2), \
         patch("plugins.boot.boot.socket.create_connection",
               return_value=return_value, side_effect=create_connection_side_effect):
        assert b._probe_home_network() is expected


@pytest.mark.parametrize("network_up, devices, should_poll_parallel", [
    (False, None, False),
    (True, [], False),
    (True, [{"id": "d1"}], True),
])
def test_poll_all_requires_network_and_devices(network_up, devices, should_poll_parallel):
    b = _make_boot()
    fetch_kwargs = {"return_value": devices} if devices is not None else {}
    with patch.object(b, "_probe_home_network", return_value=network_up), \
         patch.object(b, "_fetch_devices_from_backend", **fetch_kwargs), \
         patch.object(b, "_poll_in_parallel") as mock_par:
        b.poll_all_devices()
    assert mock_par.called is should_poll_parallel


def test_reload_and_preload_updates_cache_for_each_device():
    b = _make_boot()
    devices = [{"id": "d1", "estado": {"power": "on"}, "is_online": True},
               {"id": "d2", "estado": None, "is_online": False}]
    with patch.object(b, "_fetch_devices_from_backend", return_value=devices), \
         patch("plugins.boot.boot.device_cache") as mock_cache:
        b._reload_and_preload()
    assert mock_cache.update.call_count == 2


def test_poll_one_returns_none_when_status_is_none():
    b = _make_boot()
    driver = MagicMock()
    driver.get_status.return_value = None
    with patch.dict("plugins.boot.boot.DRIVERS", {"tuya": driver}, clear=False), \
         patch.object(b, "_sync_if_changed") as mock_sync:
        assert b._poll_one({"id": "d1", "driver": "tuya"}) is None
    mock_sync.assert_not_called()


def test_poll_in_parallel_handles_future_failures(monkeypatch):
    b = _make_boot()
    b.devices = [{"id": "d1"}, {"id": "d2"}]
    fake_future = MagicMock()
    fake_future.result.side_effect = TimeoutError("timeout")
    monkeypatch.setattr(b.executor, "submit", lambda *_a, **_k: fake_future)
    b._poll_in_parallel()
