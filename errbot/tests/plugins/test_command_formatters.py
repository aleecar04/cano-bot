

class TestFormatCommandResponse:

    def test_error_con_mensaje_se_devuelve_tal_cual(self):
        from plugins.command_formatters import format_command_response
        result = format_command_response("encender", None, "Luz", False, "Sin red")
        assert result == "Sin red"

    def test_error_sin_mensaje_y_con_device_da_fallback_legible(self):
        from plugins.command_formatters import format_command_response
        result = format_command_response("encender", None, "Luz salón", False, None)
        assert "Luz salón" in result
        assert "No pude" in result

    def test_error_sin_mensaje_ni_device_da_fallback_generico(self):
        from plugins.command_formatters import format_command_response
        result = format_command_response("scan", None, "", False, None)
        assert "No se pudo" in result

    def test_scan_con_resultado_resume_dispositivos(self):
        from plugins.command_formatters import format_command_response
        data = {"dispositivos": [{"name": "a"}, {"name": "b"}]}
        result = format_command_response("scan", data, "", True, None)
        assert "2 dispositivos" in result

    def test_scan_con_un_dispositivo_usa_singular(self):
        from plugins.command_formatters import format_command_response
        data = {"dispositivos": [{"name": "a"}]}
        result = format_command_response("scan", data, "", True, None)
        assert "1 dispositivo" in result
        assert "1 dispositivos" not in result

    def test_list_devices_resume(self):
        from plugins.command_formatters import format_command_response
        data = {"dispositivos": [{"name": "a"}, {"name": "b"}, {"name": "c"}]}
        result = format_command_response("list_devices", data, "", True, None)
        assert "3 dispositivos" in result

    def test_accion_sin_builder_da_mensaje_generico(self):
        from plugins.command_formatters import format_command_response
        result = format_command_response("encender", None, "Luz salón", True, None)
        assert "Luz salón" in result
        assert "encender" in result
