"""
Integration tests for the Scheduler errbot plugin.

The Scheduler polls the backend for pending tasks and executes them via drivers.
Tests use errbot's TestBot fixture + mocked HTTP + mocked drivers.

_check_pending_schedules and _execute_schedule are tested by retrieving the
plugin object from the bot and calling the methods directly (no message needed).
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).parent.parent.parent

extra_plugin_dir = str(ROOT / "plugins" / "scheduler")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_response(data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    return m


def _get_plugin(testbot):
    """Retrieve the Scheduler plugin instance from the running bot."""
    return testbot.bot.plugin_manager.get_plugin_obj_by_name("Scheduler")


def _set_driver(ok: bool, error: str = "timeout"):
    drivers = sys.modules["drivers"]
    if ok:
        drivers.ejecutar_comando.return_value = {"ok": True}
    else:
        drivers.ejecutar_comando.return_value = {"ok": False, "error": error}


FAKE_DEVICE = {
    "id": "dev-1",
    "name": "Luz",
    "type": "Luz",
    "driver": "tuya",
    "is_online": True,
    "estado": {"power": "off"},
}

PENDING_SCHEDULE = {
    "id": "sch-1",
    "device_id": "dev-1",
    "user_id": "uid-1",
    "action": "encender",
    "payload": {},
}


def _get_router(url, **kwargs):
    m = _make_response({})
    if "/users/by-jid/" in url:
        m.json.return_value = {"user_id": "uid-1"}
    elif "/devices/all" in url:
        m.json.return_value = [FAKE_DEVICE]
    elif "/schedules/pending" in url:
        m.json.return_value = [PENDING_SCHEDULE]
    return m


def _post_router(url, **kwargs):
    return _make_response({})


def _patch_router(url, **kwargs):
    return _make_response({})


# ── Plugin load and activation ────────────────────────────────────────────────

class TestSchedulerActivation:
    extra_plugin_dir = str(ROOT / "plugins" / "scheduler")

    def test_plugin_is_loaded(self, testbot):
        plugin = _get_plugin(testbot)
        assert plugin is not None

    def test_plugin_has_check_method(self, testbot):
        plugin = _get_plugin(testbot)
        assert hasattr(plugin, "_check_pending_schedules")

    def test_plugin_has_execute_method(self, testbot):
        plugin = _get_plugin(testbot)
        assert hasattr(plugin, "_execute_schedule")


# ── _check_pending_schedules ──────────────────────────────────────────────────

class TestCheckPendingSchedules:
    extra_plugin_dir = str(ROOT / "plugins" / "scheduler")

    def test_does_nothing_when_backend_unreachable(self, testbot):
        plugin = _get_plugin(testbot)
        with patch("plugins._core.is_backend_reachable", return_value=False):
            plugin._check_pending_schedules()  # should not raise

    def test_handles_http_error_gracefully(self, testbot):
        plugin = _get_plugin(testbot)
        with patch("plugins.state_sync.is_backend_reachable", return_value=True), \
             patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("requests.get", side_effect=Exception("connection refused")):
            plugin._check_pending_schedules()  # logs error, does not raise

    def test_calls_execute_for_each_pending(self, testbot):
        plugin = _get_plugin(testbot)
        schedules = [PENDING_SCHEDULE, {**PENDING_SCHEDULE, "id": "sch-2"}]
        with patch("plugins._core.is_backend_reachable", return_value=True), \
             patch("requests.get", return_value=_make_response(schedules, 200)), \
             patch.object(plugin, "_execute_schedule") as mock_exec:
            plugin._check_pending_schedules()
        assert mock_exec.call_count == 2


# ── _execute_schedule ─────────────────────────────────────────────────────────

class TestExecuteSchedule:
    extra_plugin_dir = str(ROOT / "plugins" / "scheduler")

    def _exec(self, testbot, schedule, driver_ok=True):
        """Call _execute_schedule with mocked HTTP and drivers."""
        _set_driver(driver_ok)
        plugin = _get_plugin(testbot)
        with patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router):
            plugin._execute_schedule(schedule)

    def test_execute_ok_calls_mark_run(self, testbot):
        with patch("requests.get",   side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post",  side_effect=_post_router) as mock_post:
            _set_driver(True)
            _get_plugin(testbot)._execute_schedule(PENDING_SCHEDULE)
        # mark-run must have been called via POST
        called_urls = [call.args[0] for call in mock_post.call_args_list]
        assert any("mark-run" in u for u in called_urls)

    def test_execute_device_not_found_marks_error(self, testbot):
        def no_device_get(url, **kwargs):
            m = _make_response({})
            if "/devices/all" in url:
                m.json.return_value = []  # empty → device not found
            return m

        plugin = _get_plugin(testbot)
        with patch("requests.get",  side_effect=no_device_get), \
             patch("requests.post", side_effect=_post_router) as mock_post:
            plugin._execute_schedule(PENDING_SCHEDULE)

        called_urls = [call.args[0] for call in mock_post.call_args_list]
        assert any("mark-run" in u for u in called_urls)

    def test_execute_driver_failure_marks_error(self, testbot):
        self._exec(testbot, PENDING_SCHEDULE, driver_ok=False)
        # No exception should propagate

    def test_execute_success_updates_cache(self, testbot):
        from plugins.device_cache import device_cache
        device_cache.clear()
        self._exec(testbot, PENDING_SCHEDULE, driver_ok=True)
        state = device_cache.get("dev-1")
        assert state is not None
        assert state.is_online is True

    def test_mark_run_http_error_does_not_raise(self, testbot):
        plugin = _get_plugin(testbot)
        with patch("requests.get",  side_effect=_get_router), \
             patch("requests.patch", side_effect=_patch_router), \
             patch("requests.post", side_effect=Exception("server error")):
            _set_driver(True)
            plugin._execute_schedule(PENDING_SCHEDULE)  # should not raise
