from unittest.mock import patch

import pytest


@pytest.mark.parametrize("name, value", [
    ("TUYA", "tuya"),
    ("LG_TV", "lg_tv"),
    ("SAMSUNG_TV", "samsung_tv"),
    ("HOMEASSISTANT", "homeassistant"),
    ("GENERIC", "generic"),
])
def test_driver_type_enum_values(name, value):
    from drivers import DriverType
    assert getattr(DriverType, name) == value


def test_ejecutar_comando_returns_error_for_unknown_driver():
    from drivers import ejecutar_comando
    result = ejecutar_comando({"driver": "no-existe"}, "encender", {})
    assert result["ok"] is False and "no reconocido" in result["error"]


def test_ejecutar_comando_delegates_to_corresponding_driver():
    from drivers import ejecutar_comando, DRIVERS, DriverType
    with patch.object(DRIVERS[DriverType.TUYA], "ejecutar",
                      return_value={"ok": True, "marker": "tuya"}) as mock_exec:
        result = ejecutar_comando({"driver": DriverType.TUYA}, "encender", {"foo": "bar"})
    assert result == {"ok": True, "marker": "tuya"}
    assert mock_exec.call_args[0][2] == {"foo": "bar"}
