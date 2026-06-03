from unittest.mock import patch, MagicMock


class TestGetSupportedActions:

    def test_tipo_luz_incluye_brillo(self):
        from plugins.help.help import get_supported_actions
        from drivers.actions_catalog import Action
        actions = get_supported_actions("Luz")
        assert Action.BRILLO in actions
        assert Action.ENCENDER in actions

    def test_tipo_enchufe_solo_basicos(self):
        from plugins.help.help import get_supported_actions
        from drivers.actions_catalog import Action
        actions = get_supported_actions("Enchufe")
        assert Action.ENCENDER in actions
        assert Action.BRILLO not in actions

    def test_tipo_smarttv_incluye_volumen_y_apps(self):
        from plugins.help.help import get_supported_actions
        from drivers.actions_catalog import Action
        actions = get_supported_actions("SmartTV")
        assert Action.SET_VOLUMEN in actions
        assert Action.ABRIR_APP in actions

    def test_tipo_ha_light_se_mapea_a_luz(self):
        """Tipo 'light' (Home Assistant) usa las mismas acciones que 'Luz'."""
        from plugins.help.help import get_supported_actions
        from drivers.actions_catalog import Action
        actions = get_supported_actions("light")
        assert Action.BRILLO in actions

    def test_tipo_desconocido_devuelve_vacio(self):
        from plugins.help.help import get_supported_actions
        assert get_supported_actions("AspiradoraRobot") == set()


class TestFormatHelpers:

    def test_format_actions_for_device_incluye_nombre_y_categoria(self):
        from plugins.help.help import _format_actions_for_device
        result = _format_actions_for_device({"name": "Luz Salón", "type": "Luz"})
        assert "Luz Salón" in result
        assert "Luz / Bombilla" in result
        assert "encender" in result

    def test_format_actions_by_category_lista_categorias(self):
        from plugins.help.help import _format_actions_by_category
        result = _format_actions_by_category()
        assert "Luz / Bombilla" in result
        assert "Smart TV" in result
        assert "Enchufe / Interruptor" in result


def _make_help():
    from plugins.help.help import Help
    h = Help.__new__(Help)
    h.log = MagicMock()
    return h


class TestHelpPluginCommands:

    def test_ayuda_devuelve_help_text(self):
        from plugins.help.help import HELP_TEXT
        h = _make_help()
        msg = MagicMock(frm="alice@x")
        result = h.ayuda(msg, "")
        assert result == HELP_TEXT

    def test_acciones_sin_args_devuelve_listado_completo(self):
        h = _make_help()
        msg = MagicMock(frm="alice@x")
        result = h.acciones(msg, "")
        assert "Luz / Bombilla" in result

    def test_acciones_con_device_existente_devuelve_acciones(self):
        h = _make_help()
        msg = MagicMock(frm="alice@x")
        device = {"id": "d1", "name": "Lámpara", "type": "Luz"}
        with patch("plugins.help.help.find_device_by_name", return_value=device):
            result = h.acciones(msg, "lámpara")
        assert "Lámpara" in result
        assert "encender" in result

    def test_acciones_con_device_inexistente_devuelve_error(self):
        h = _make_help()
        msg = MagicMock(frm="alice@x")
        with patch("plugins.help.help.find_device_by_name", return_value=None):
            result = h.acciones(msg, "ghost")
        assert "No he encontrado" in result
        assert "ghost" in result
