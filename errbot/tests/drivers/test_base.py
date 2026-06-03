from unittest.mock import MagicMock


def _make_concrete():
    """Subclase mínima que cumple el contrato abstracto sin sobreescribir más."""
    from drivers.base import BaseDriver

    class Concrete(BaseDriver):
        def get_status(self, device, timeout=2.0):
            return {"is_online": True}
        def encender(self, device):
            return {"ok": True}
        def apagar(self, device):
            return {"ok": True}
    return Concrete()


# ── Defaults "no soportado" en BaseDriver ────────────────────────────────────

class TestDefaultsNoSoportado:

    def test_brillo_default(self):
        result = _make_concrete().brillo({}, 50)
        assert result["ok"] is False
        assert "brillo" in result["error"].lower()

    def test_temperatura_color_default(self):
        result = _make_concrete().temperatura_color({}, 4000)
        assert result["ok"] is False

    def test_color_rgb_default(self):
        result = _make_concrete().color_rgb({}, 255, 0, 0)
        assert result["ok"] is False

    def test_set_volumen_default(self):
        result = _make_concrete().set_volumen({}, 50)
        assert result["ok"] is False

    def test_abrir_app_default(self):
        result = _make_concrete().abrir_app({}, "netflix")
        assert result["ok"] is False


# ── _dispatch_color (mapeo nombre → RGB) ─────────────────────────────────────

class TestDispatchColor:

    def test_nombre_conocido_invoca_color_rgb_con_tupla(self):
        drv = _make_concrete()
        drv.color_rgb = MagicMock(return_value={"ok": True})
        drv._dispatch_color({}, {"color": "rojo"})
        drv.color_rgb.assert_called_once()
        args = drv.color_rgb.call_args[0]
        # device, r, g, b
        assert args[1:] == (255, 0, 0)

    def test_nombre_desconocido_devuelve_error(self):
        result = _make_concrete()._dispatch_color({}, {"color": "salmon"})
        assert result["ok"] is False
        assert "salmon" in result["error"].lower()

    def test_sin_color_pero_con_rgb_explicito(self):
        drv = _make_concrete()
        drv.color_rgb = MagicMock(return_value={"ok": True})
        drv._dispatch_color({}, {"r": 100, "g": 200, "b": 50})
        args = drv.color_rgb.call_args[0]
        assert args[1:] == (100, 200, 50)

    def test_sin_payload_usa_defaults_rojo(self):
        drv = _make_concrete()
        drv.color_rgb = MagicMock(return_value={"ok": True})
        drv._dispatch_color({}, {})
        args = drv.color_rgb.call_args[0]
        # defaults: r=255, g=0, b=0
        assert args[1:] == (255, 0, 0)


# ── ejecutar (dispatcher por action) ─────────────────────────────────────────

class TestEjecutar:

    def test_accion_desconocida_devuelve_error(self):
        result = _make_concrete().ejecutar({}, "accion_inventada", {})
        assert result["ok"] is False
        assert "no soportada" in result["error"]

    def test_encender_dispatcha_a_encender(self):
        drv = _make_concrete()
        drv.encender = MagicMock(return_value={"ok": True, "marker": "enc"})
        result = drv.ejecutar({}, "encender", {})
        assert result["marker"] == "enc"

    def test_apagar_dispatcha_a_apagar(self):
        drv = _make_concrete()
        drv.apagar = MagicMock(return_value={"ok": True, "marker": "apa"})
        result = drv.ejecutar({}, "apagar", {})
        assert result["marker"] == "apa"

    def test_brillo_pasa_valor_del_payload(self):
        drv = _make_concrete()
        drv.brillo = MagicMock(return_value={"ok": True})
        drv.ejecutar({}, "brillo", {"valor": 75})
        assert drv.brillo.call_args[0][1] == 75

    def test_brillo_sin_valor_usa_default(self):
        drv = _make_concrete()
        drv.brillo = MagicMock(return_value={"ok": True})
        drv.ejecutar({}, "brillo", {})
        assert drv.brillo.call_args[0][1] == 100

    def test_temperatura_color_pasa_valor(self):
        drv = _make_concrete()
        drv.temperatura_color = MagicMock(return_value={"ok": True})
        drv.ejecutar({}, "temperatura_color", {"valor": 2700})
        assert drv.temperatura_color.call_args[0][1] == 2700

    def test_color_rgb_va_por_dispatch_color(self):
        drv = _make_concrete()
        drv.color_rgb = MagicMock(return_value={"ok": True})
        drv.ejecutar({}, "color_rgb", {"color": "azul"})
        # _dispatch_color tradujo a (0, 0, 255)
        args = drv.color_rgb.call_args[0]
        assert args[1:] == (0, 0, 255)

    def test_set_volumen_pasa_valor(self):
        drv = _make_concrete()
        drv.set_volumen = MagicMock(return_value={"ok": True})
        drv.ejecutar({}, "set_volumen", {"valor": 30})
        assert drv.set_volumen.call_args[0][1] == 30

    def test_abrir_app_pasa_nombre(self):
        drv = _make_concrete()
        drv.abrir_app = MagicMock(return_value={"ok": True})
        drv.ejecutar({}, "abrir_app", {"app": "netflix"})
        assert drv.abrir_app.call_args[0][1] == "netflix"

    def test_excepcion_del_metodo_devuelve_error(self):
        drv = _make_concrete()
        drv.encender = MagicMock(side_effect=RuntimeError("boom"))
        result = drv.ejecutar({}, "encender", {})
        assert result["ok"] is False
        assert "boom" in result["error"]
