import pytest

from plugins.command_formatters import format_command_response


def test_error_path_uses_provided_message_verbatim():
    assert format_command_response("encender", None, "Luz", False, "Sin red") == "Sin red"


def test_error_path_falls_back_with_device_name_when_no_message():
    result = format_command_response("encender", None, "Luz salón", False, None)
    assert "Luz salón" in result and "No pude" in result


def test_error_path_falls_back_to_generic_when_no_device():
    assert "No se pudo" in format_command_response("scan", None, "", False, None)


@pytest.mark.parametrize("count, expected_text", [
    (1, "1 dispositivo"),
    (3, "3 dispositivos"),
])
def test_scan_renders_pluralized_count(count, expected_text):
    data = {"dispositivos": [{"name": f"d{i}"} for i in range(count)]}
    assert expected_text in format_command_response("scan", data, "", True, None)


def test_list_devices_renders_pluralized_count():
    data = {"dispositivos": [{"name": "a"}, {"name": "b"}, {"name": "c"}]}
    assert "3 dispositivos" in format_command_response("list_devices", data, "", True, None)


def test_action_without_specific_builder_uses_generic_message():
    result = format_command_response("encender", None, "Luz salón", True, None)
    assert "Luz salón" in result and "encender" in result
