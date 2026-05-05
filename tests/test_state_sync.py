"""Tests for plugins/state_sync.py — StateSync pure logic (no real network)."""
import time
import pytest
from unittest.mock import patch, MagicMock, call
from plugins.state_sync import StateSync
from plugins.device_cache import DeviceState


# ── Helpers ───────────────────────────────────────────────────────────────────

def _state(device_id="dev-1", is_online=True, last_update=None, confidence=1.0):
    return DeviceState(
        device_id=device_id,
        estado={"power": "on"},
        is_online=is_online,
        last_update=last_update if last_update is not None else time.time(),
        source="action",
        confidence=confidence,
    )


# ── mark_device_changed ───────────────────────────────────────────────────────

def test_mark_device_changed_adds_to_pending():
    sync = StateSync()
    sync.mark_device_changed("dev-1", _state())
    assert "dev-1" in sync.pending_changes


def test_mark_device_changed_overwrites_previous():
    sync = StateSync()
    sync.mark_device_changed("dev-1", _state(is_online=True))
    sync.mark_device_changed("dev-1", _state(is_online=False))
    assert sync.pending_changes["dev-1"].is_online is False


def test_mark_device_changed_multiple_devices():
    sync = StateSync()
    sync.mark_device_changed("dev-1", _state("dev-1"))
    sync.mark_device_changed("dev-2", _state("dev-2"))
    assert set(sync.pending_changes.keys()) == {"dev-1", "dev-2"}


# ── sync_pending_changes ──────────────────────────────────────────────────────

def test_sync_does_nothing_when_no_pending():
    sync = StateSync()
    with patch("plugins.state_sync.is_backend_reachable", return_value=True):
        sync.sync_pending_changes()
    assert sync.syncs_completed == 0


def test_sync_does_nothing_when_backend_unreachable():
    sync = StateSync()
    sync.mark_device_changed("dev-1", _state())
    with patch("plugins.state_sync.is_backend_reachable", return_value=False):
        sync.sync_pending_changes()
    # Change still pending
    assert "dev-1" in sync.pending_changes


def test_sync_clears_pending_on_success():
    sync = StateSync()
    sync.mark_device_changed("dev-1", _state())
    with patch("plugins.state_sync.is_backend_reachable", return_value=True), \
         patch.object(sync, "_patch_device_status"):
        sync.sync_pending_changes()
    assert sync.pending_changes == {}
    assert sync.syncs_completed == 1


def test_sync_enqueues_retry_on_failure():
    sync = StateSync()
    sync.mark_device_changed("dev-1", _state())
    with patch("plugins.state_sync.is_backend_reachable", return_value=True), \
         patch.object(sync, "_patch_device_status", side_effect=Exception("net")):
        sync.sync_pending_changes()
    assert sync.syncs_failed == 1
    assert len(sync.retry_queue) == 1
    assert sync.retry_queue[0]["device_id"] == "dev-1"


def test_sync_multiple_devices_all_processed():
    sync = StateSync()
    sync.mark_device_changed("a", _state("a"))
    sync.mark_device_changed("b", _state("b"))
    with patch("plugins.state_sync.is_backend_reachable", return_value=True), \
         patch.object(sync, "_patch_device_status"):
        sync.sync_pending_changes()
    assert sync.syncs_completed == 2
    assert sync.pending_changes == {}


# ── Retry backoff ────────────────────────────────────────────────────────────

def test_item_not_retried_before_backoff():
    """Item with retries=1 needs 2^1=2s backoff; if just queued it should be skipped."""
    sync = StateSync()
    item = {"device_id": "dev-1", "state": _state(), "retries": 1, "timestamp": time.time()}
    sync.retry_queue.append(item)
    with patch.object(sync, "_attempt_retry") as mock_attempt:
        sync._process_retries()
    mock_attempt.assert_not_called()


def test_item_retried_after_backoff_elapsed():
    """Item with retries=0 needs 2^0=1s backoff; 5s elapsed is enough."""
    sync = StateSync()
    item = {"device_id": "dev-1", "state": _state(), "retries": 0, "timestamp": time.time() - 5}
    sync.retry_queue.append(item)
    with patch.object(sync, "_attempt_retry") as mock_attempt:
        sync._process_retries()
    mock_attempt.assert_called_once_with(item)


def test_successful_retry_removes_from_queue():
    sync = StateSync()
    item = {"device_id": "dev-1", "state": _state(), "retries": 0, "timestamp": time.time() - 5}
    sync.retry_queue.append(item)
    with patch.object(sync, "_patch_device_status"):
        sync._attempt_retry(item)
    assert len(sync.retry_queue) == 0


def test_failed_retry_increments_retries():
    sync = StateSync(max_retries=3)
    item = {"device_id": "dev-1", "state": _state(), "retries": 0, "timestamp": time.time()}
    sync.retry_queue.append(item)
    with patch.object(sync, "_patch_device_status", side_effect=Exception("fail")):
        sync._attempt_retry(item)
    assert item["retries"] == 1
    assert len(sync.retry_queue) == 1  # still there


def test_max_retries_discards_item():
    sync = StateSync(max_retries=3)
    item = {"device_id": "dev-1", "state": _state(), "retries": 2, "timestamp": time.time()}
    sync.retry_queue.append(item)
    with patch.object(sync, "_patch_device_status", side_effect=Exception("fail")):
        sync._attempt_retry(item)
    assert len(sync.retry_queue) == 0  # discarded after max_retries


def test_empty_retry_queue_does_nothing():
    sync = StateSync()
    sync._process_retries()  # no error, no crash


# ── _patch_device_status ──────────────────────────────────────────────────────

def test_patch_device_status_sends_correct_payload():
    sync = StateSync()
    state = _state("dev-1", is_online=True)
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("requests.patch", return_value=mock_resp) as mock_patch:
        sync._patch_device_status("dev-1", state)
    mock_patch.assert_called_once()
    sent = mock_patch.call_args.kwargs["json"]
    assert sent["is_online"] is True
    assert "estado" in sent
    assert "source" in sent


def test_patch_device_status_raises_on_error():
    sync = StateSync()
    state = _state()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("500")
    with patch("requests.patch", return_value=mock_resp):
        with pytest.raises(Exception):
            sync._patch_device_status("dev-1", state)


# ── full_reconciliation ───────────────────────────────────────────────────────

def test_full_reconciliation_skips_when_backend_unreachable():
    sync = StateSync()
    with patch("plugins.state_sync.is_backend_reachable", return_value=False), \
         patch.object(sync, "_reconcile_device") as mock_rec:
        sync.full_reconciliation()
    mock_rec.assert_not_called()


def test_full_reconciliation_processes_all_cached_devices():
    from plugins.device_cache import DeviceStateCache
    sync = StateSync()
    cache = DeviceStateCache()
    cache.update("a", {}, is_online=True)
    cache.update("b", {}, is_online=True)

    with patch("plugins.state_sync.is_backend_reachable", return_value=True), \
         patch("plugins.state_sync.device_cache", cache), \
         patch.object(sync, "_reconcile_device") as mock_rec:
        sync.full_reconciliation()

    assert mock_rec.call_count == 2
    assert sync.reconciliation_count == 1


def test_reconcile_device_updates_cache_when_backend_newer():
    import time
    from plugins.device_cache import DeviceStateCache

    sync = StateSync()
    cache = DeviceStateCache()
    local = cache.update("dev-1", {"power": "off"}, is_online=True)

    backend_state = {
        "estado": {"power": "on"},
        "is_online": True,
        "last_update": "2099-01-01T00:00:00+00:00",
    }

    with patch("plugins.state_sync.device_cache", cache), \
         patch.object(sync, "_fetch_device_status", return_value=backend_state):
        sync._reconcile_device("dev-1", local)

    assert cache.get("dev-1").estado["power"] == "on"


def test_reconcile_device_skips_when_local_is_newer():
    from plugins.device_cache import DeviceStateCache
    sync = StateSync()
    cache = DeviceStateCache()
    local = cache.update("dev-1", {"power": "off"}, is_online=True)

    backend_state = {
        "estado": {"power": "on"},
        "is_online": True,
        "last_update": "2000-01-01T00:00:00+00:00",  # older
    }

    with patch("plugins.state_sync.device_cache", cache), \
         patch.object(sync, "_fetch_device_status", return_value=backend_state):
        sync._reconcile_device("dev-1", local)

    # Cache should NOT be updated
    assert cache.get("dev-1").estado["power"] == "off"


def test_reconcile_device_handles_fetch_error():
    sync = StateSync()
    local = _state("dev-1")
    with patch.object(sync, "_fetch_device_status", side_effect=Exception("404")):
        sync._reconcile_device("dev-1", local)  # must not raise


def test_fetch_device_status_returns_json():
    sync = StateSync()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"is_online": True, "estado": {}}
    with patch("requests.get", return_value=mock_resp):
        result = sync._fetch_device_status("dev-1")
    assert result["is_online"] is True


# ── get_stats ────────────────────────────────────────────────────────────────

def test_get_stats_initial():
    sync = StateSync()
    s = sync.get_stats()
    assert s == {
        "pending_changes": 0,
        "retry_queue": 0,
        "syncs_completed": 0,
        "syncs_failed": 0,
        "reconciliations": 0,
    }


def test_get_stats_reflects_state():
    sync = StateSync()
    sync.mark_device_changed("x", _state())
    sync.syncs_completed = 7
    sync.syncs_failed = 3
    sync.reconciliation_count = 2
    s = sync.get_stats()
    assert s["pending_changes"] == 1
    assert s["syncs_completed"] == 7
    assert s["syncs_failed"] == 3
    assert s["reconciliations"] == 2
