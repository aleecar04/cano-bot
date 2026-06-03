from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor


def _make_boot():
    """Construye Boot sin pasar por errbot init (que requiere bot)."""
    from plugins.boot.boot import Boot
    b = Boot.__new__(Boot)
    b.devices = []
    b.executor = ThreadPoolExecutor(max_workers=2)
    return b


# ── _fetch_devices_from_backend ─────────────────────────────────────────────

class TestFetchDevices:

    def test_devuelve_lista_previa_si_no_reachable(self):
        b = _make_boot()
        b.devices = [{"id": "old"}]
        with patch("plugins.boot.boot.is_backend_reachable", return_value=False):
            result = b._fetch_devices_from_backend()
        assert result == [{"id": "old"}]

    def test_devuelve_lista_nueva_si_api_ok(self):
        b = _make_boot()
        new = [{"id": "new1"}, {"id": "new2"}]
        with patch("plugins.boot.boot.is_backend_reachable", return_value=True), \
             patch("plugins.boot.boot.api_devices.get_all", return_value=new):
            result = b._fetch_devices_from_backend()
        assert result == new

    def test_devuelve_lista_previa_si_api_falla(self):
        b = _make_boot()
        b.devices = [{"id": "old"}]
        with patch("plugins.boot.boot.is_backend_reachable", return_value=True), \
             patch("plugins.boot.boot.api_devices.get_all", side_effect=RuntimeError("boom")):
            result = b._fetch_devices_from_backend()
        assert result == [{"id": "old"}]


# ── _reload_and_preload ─────────────────────────────────────────────────────

class TestReloadAndPreload:

    def test_carga_devices_y_actualiza_cache(self):
        b = _make_boot()
        devs = [{"id": "d1", "estado": {"power": "on"}, "is_online": True}]
        with patch.object(b, "_fetch_devices_from_backend", return_value=devs), \
             patch("plugins.boot.boot.device_cache.update") as mock_upd:
            b._reload_and_preload()
        assert b.devices == devs
        mock_upd.assert_called_once_with(device_id="d1", estado={"power": "on"}, is_online=True)


# ── _patch_backend ──────────────────────────────────────────────────────────

class TestPatchBackend:

    def test_skip_si_no_reachable(self):
        b = _make_boot()
        with patch("plugins.boot.boot.is_backend_reachable", return_value=False), \
             patch("plugins.boot.boot.api_devices.patch_status") as mock_p:
            b._patch_backend("d1", True, {"power": "on"})
        mock_p.assert_not_called()

    def test_actualiza_cache_solo_si_patch_exitoso(self):
        b = _make_boot()
        with patch("plugins.boot.boot.is_backend_reachable", return_value=True), \
             patch("plugins.boot.boot.api_devices.patch_status"), \
             patch("plugins.boot.boot.device_cache.update") as mock_upd:
            b._patch_backend("d1", True, {"power": "on"})
        mock_upd.assert_called_once()

    def test_no_actualiza_cache_si_patch_falla(self):
        b = _make_boot()
        with patch("plugins.boot.boot.is_backend_reachable", return_value=True), \
             patch("plugins.boot.boot.api_devices.patch_status", side_effect=RuntimeError("net")), \
             patch("plugins.boot.boot.device_cache.update") as mock_upd:
            b._patch_backend("d1", True, {"power": "on"})
        mock_upd.assert_not_called()


# ── _sync_if_changed ────────────────────────────────────────────────────────

class TestSyncIfChanged:

    def test_no_actualiza_si_estado_y_online_son_iguales(self):
        b = _make_boot()
        cached = MagicMock(is_online=True, estado={"power": "on"})
        with patch("plugins.boot.boot.device_cache.get", return_value=cached), \
             patch.object(b, "_patch_backend") as mock_patch:
            b._sync_if_changed("d1", {"is_online": True, "estado": {"power": "on"}})
        mock_patch.assert_not_called()

    def test_actualiza_si_estado_cambio(self):
        b = _make_boot()
        cached = MagicMock(is_online=True, estado={"power": "on"})
        with patch("plugins.boot.boot.device_cache.get", return_value=cached), \
             patch.object(b, "_patch_backend") as mock_patch:
            b._sync_if_changed("d1", {"is_online": True, "estado": {"power": "off"}})
        mock_patch.assert_called_once()

    def test_actualiza_si_no_hay_cache(self):
        b = _make_boot()
        with patch("plugins.boot.boot.device_cache.get", return_value=None), \
             patch.object(b, "_patch_backend") as mock_patch:
            b._sync_if_changed("d1", {"is_online": True, "estado": {}})
        mock_patch.assert_called_once()


# ── _sync_offline ───────────────────────────────────────────────────────────

class TestSyncOffline:

    def test_no_actualiza_si_ya_estaba_offline(self):
        b = _make_boot()
        cached = MagicMock(is_online=False, estado={"power": "off"})
        with patch("plugins.boot.boot.device_cache.get", return_value=cached), \
             patch.object(b, "_patch_backend") as mock_patch:
            b._sync_offline("d1")
        mock_patch.assert_not_called()

    def test_marca_offline_si_estaba_online(self):
        b = _make_boot()
        cached = MagicMock(is_online=True, estado={"power": "on"})
        with patch("plugins.boot.boot.device_cache.get", return_value=cached), \
             patch.object(b, "_patch_backend") as mock_patch:
            b._sync_offline("d1")
        mock_patch.assert_called_once()
        assert mock_patch.call_args.kwargs["is_online"] is False


# ── _poll_one ───────────────────────────────────────────────────────────────

class TestPollOne:

    def test_driver_desconocido_devuelve_none(self):
        b = _make_boot()
        result = b._poll_one({"id": "d1", "driver": "noexiste"})
        assert result is None

    def test_status_none_devuelve_none(self):
        b = _make_boot()
        mock_driver = MagicMock()
        mock_driver.get_status.return_value = None
        with patch.dict("plugins.boot.boot.DRIVERS", {"tuya": mock_driver}):
            result = b._poll_one({"id": "d1", "driver": "tuya"})
        assert result is None

    def test_excepcion_en_driver_marca_offline(self):
        b = _make_boot()
        mock_driver = MagicMock()
        mock_driver.get_status.side_effect = RuntimeError("boom")
        with patch.dict("plugins.boot.boot.DRIVERS", {"tuya": mock_driver}), \
             patch.object(b, "_sync_offline") as mock_off:
            result = b._poll_one({"id": "d1", "driver": "tuya", "name": "Luz"})
        assert result is None
        mock_off.assert_called_once_with("d1")

    def test_status_valido_sincroniza_y_devuelve(self):
        b = _make_boot()
        mock_driver = MagicMock()
        status = {"is_online": True, "estado": {"power": "on"}}
        mock_driver.get_status.return_value = status
        with patch.dict("plugins.boot.boot.DRIVERS", {"tuya": mock_driver}), \
             patch.object(b, "_sync_if_changed") as mock_sync:
            result = b._poll_one({"id": "d1", "driver": "tuya"})
        assert result == status
        mock_sync.assert_called_once_with("d1", status)


# ── _probe_home_network ─────────────────────────────────────────────────────

class TestProbeHomeNetwork:

    def test_devuelve_false_si_no_hay_gateway(self):
        b = _make_boot()
        with patch("plugins.boot.boot.netifaces.gateways", return_value={"default": {}}):
            assert b._probe_home_network() is False

    def test_devuelve_false_si_netifaces_lanza(self):
        b = _make_boot()
        with patch("plugins.boot.boot.netifaces.gateways", side_effect=RuntimeError):
            assert b._probe_home_network() is False

    def test_devuelve_true_si_conexion_exitosa(self):
        b = _make_boot()
        gw = {"default": {2: ("192.168.1.1", "eth0")}}  # AF_INET=2
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        with patch("plugins.boot.boot.netifaces.gateways", return_value=gw), \
             patch("plugins.boot.boot.netifaces.AF_INET", 2), \
             patch("plugins.boot.boot.socket.create_connection", return_value=mock_conn):
            assert b._probe_home_network() is True

    def test_devuelve_true_si_connection_refused(self):
        """ConnectionRefusedError significa que el host existe pero el puerto cerrado — red OK."""
        b = _make_boot()
        gw = {"default": {2: ("192.168.1.1", "eth0")}}
        with patch("plugins.boot.boot.netifaces.gateways", return_value=gw), \
             patch("plugins.boot.boot.netifaces.AF_INET", 2), \
             patch("plugins.boot.boot.socket.create_connection",
                   side_effect=ConnectionRefusedError):
            assert b._probe_home_network() is True

    def test_devuelve_false_si_todos_los_puertos_dan_oserror(self):
        b = _make_boot()
        gw = {"default": {2: ("192.168.1.1", "eth0")}}
        with patch("plugins.boot.boot.netifaces.gateways", return_value=gw), \
             patch("plugins.boot.boot.netifaces.AF_INET", 2), \
             patch("plugins.boot.boot.socket.create_connection", side_effect=OSError):
            assert b._probe_home_network() is False


# ── poll_all_devices ────────────────────────────────────────────────────────

class TestPollAllDevices:

    def test_skip_si_no_hay_red(self):
        b = _make_boot()
        with patch.object(b, "_probe_home_network", return_value=False), \
             patch.object(b, "_fetch_devices_from_backend") as mock_fetch:
            b.poll_all_devices()
        mock_fetch.assert_not_called()

    def test_skip_si_no_hay_devices(self):
        b = _make_boot()
        with patch.object(b, "_probe_home_network", return_value=True), \
             patch.object(b, "_fetch_devices_from_backend", return_value=[]), \
             patch.object(b, "_poll_in_parallel") as mock_par:
            b.poll_all_devices()
        mock_par.assert_not_called()

    def test_sondea_devices_si_todo_ok(self):
        b = _make_boot()
        with patch.object(b, "_probe_home_network", return_value=True), \
             patch.object(b, "_fetch_devices_from_backend", return_value=[{"id": "d1"}]), \
             patch.object(b, "_poll_in_parallel") as mock_par:
            b.poll_all_devices()
        mock_par.assert_called_once()
