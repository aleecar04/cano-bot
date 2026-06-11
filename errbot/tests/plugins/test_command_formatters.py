from plugins.command_formatters import format_command_response


class TestCommandFormatters:

    def test_error_path_uses_provided_message_verbatim(self):
        assert format_command_response("encender", None, "Lampara Salon", False, "Sin red") == "Sin red"

    def test_error_path_falls_back_to_generic_when_no_device(self):
        assert "No se pudo" in format_command_response("scan", None, "", False, None)

    def test_scan_renders_pluralized_count(self):
        data = {"dispositivos": [{"name": "device_lampara"}]}
        assert "1 dispositivo" in format_command_response("scan", data, "", True, None)

    def test_list_devices_renders_pluralized_count(self):
        data = {"dispositivos": [{"name": "a"}, {"name": "b"}, {"name": "c"}]}
        assert "3 dispositivos" in format_command_response("list_devices", data, "", True, None)
