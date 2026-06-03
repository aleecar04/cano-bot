import json
from unittest.mock import MagicMock, patch


# ── _patch_device_status (helper privado) ───────────────────────────────────

class TestPatchDeviceStatus:

    def test_skip_si_backend_no_reachable(self):
        from plugins.control.control import _patch_device_status
        with patch("plugins.control.control.is_backend_reachable", return_value=False), \
             patch("plugins.control.control.api_devices.patch_status") as mock_patch:
            _patch_device_status("d1", True, {"power": "on"})
        mock_patch.assert_not_called()

    def test_llama_api_si_reachable(self):
        from plugins.control.control import _patch_device_status
        with patch("plugins.control.control.is_backend_reachable", return_value=True), \
             patch("plugins.control.control.api_devices.patch_status") as mock_patch:
            _patch_device_status("d1", True, {"power": "on"})
        mock_patch.assert_called_once_with("d1", True, {"power": "on"}, timeout=5)

    def test_silencia_exception_del_api(self):
        from plugins.control.control import _patch_device_status
        with patch("plugins.control.control.is_backend_reachable", return_value=True), \
             patch("plugins.control.control.api_devices.patch_status",
                   side_effect=RuntimeError("boom")):
            _patch_device_status("d1", True, {})  # no lanza


# ── Control.control_device ─────────────────────────────────────────────────

def _make_control():
    """Crea una instancia de Control sin pasar por errbot.BotPlugin (que requiere bot)."""
    from plugins.control.control import Control
    ctrl = Control.__new__(Control)
    ctrl.log = MagicMock()
    return ctrl


class TestControlDevice:

    def test_device_no_encontrado_devuelve_error(self):
        ctrl = _make_control()
        msg = MagicMock(frm="alice@x")
        args = json.dumps({"device_id": "no-existe", "action": "encender", "payload": {}})
        with patch("plugins.control.control.get_device", return_value=None):
            result = ctrl.control_device(msg, args)
        assert result["ok"] is False
        assert "no encontrado" in result["error"].lower()

    def test_args_invalidos_devuelve_error(self):
        ctrl = _make_control()
        msg = MagicMock(frm="alice@x")
        result = ctrl.control_device(msg, "not-json")
        assert result["ok"] is False

    def test_ejecuta_y_devuelve_resultado_ok(self):
        ctrl = _make_control()
        msg = MagicMock(frm="alice@x")
        args = json.dumps({"device_id": "d1", "action": "encender", "payload": {}})
        device = {"id": "d1", "type": "Luz", "driver": "tuya", "name": "Luz"}
        with patch("plugins.control.control.get_device", return_value=device), \
             patch("plugins.control.control.ejecutar_comando",
                   return_value={"ok": True}), \
             patch("plugins.control.control._patch_device_status"):
            result = ctrl.control_device(msg, args)
        assert result["ok"] is True

    def test_error_en_driver_marca_offline(self):
        ctrl = _make_control()
        msg = MagicMock(frm="alice@x")
        args = json.dumps({"device_id": "d1", "action": "encender", "payload": {}})
        device = {"id": "d1", "type": "Luz", "driver": "tuya", "name": "Luz"}
        with patch("plugins.control.control.get_device", return_value=device), \
             patch("plugins.control.control.ejecutar_comando",
                   return_value={"ok": False, "error": "no conecta"}), \
             patch("plugins.control.control._patch_device_status") as mock_patch:
            ctrl.control_device(msg, args)
        # Cuando ok=False se llama a patch con is_online=False (kwarg)
        mock_patch.assert_called_once()
        assert mock_patch.call_args.kwargs["is_online"] is False


# ── Control.list_devices ────────────────────────────────────────────────────

class TestListDevices:

    def test_devuelve_dispositivos_serializados(self):
        ctrl = _make_control()
        msg = MagicMock(frm="alice@x")
        devices = [
            {"id": "d1", "name": "Luz", "type": "Luz", "driver": "tuya", "is_online": True, "estado": {"power": "on"}},
            {"id": "d2", "name": "TV", "type": "SmartTV", "driver": "lg_tv", "is_online": False, "estado": {}},
        ]
        with patch("plugins.control.control.api_devices.get_all", return_value=devices):
            result = ctrl.list_devices(msg, "")
        assert result["tipo"] == "device_list"
        assert result["total"] == 2
        assert len(result["dispositivos"]) == 2
        assert result["dispositivos"][0]["id"] == "d1"

    def test_excepcion_devuelve_tipo_error(self):
        ctrl = _make_control()
        msg = MagicMock(frm="alice@x")
        with patch("plugins.control.control.api_devices.get_all",
                   side_effect=RuntimeError("boom")):
            result = ctrl.list_devices(msg, "")
        assert result["tipo"] == "error"
        assert "boom" in result["mensaje"]


# ── Control._serialize_device ───────────────────────────────────────────────

class TestSerializeDevice:

    def test_usa_cache_si_existe(self):
        from plugins.control.control import Control
        from plugins.device_cache import device_cache
        device_cache.update("d1", estado={"power": "on"}, is_online=True)
        result = Control._serialize_device({
            "id": "d1", "name": "Luz", "type": "Luz", "driver": "tuya",
            "is_online": False, "estado": {},
        })
        # El cache gana sobre el dict del backend
        assert result["is_online"] is True
        assert result["estado"] == {"power": "on"}

    def test_fallback_al_dict_si_no_hay_cache(self):
        from plugins.control.control import Control
        result = Control._serialize_device({
            "id": "no-cache", "name": "X", "type": "Luz", "driver": "tuya",
            "is_online": True, "estado": {"power": "on"},
        })
        assert result["is_online"] is True
        assert result["estado"] == {"power": "on"}
