from unittest.mock import patch

from drivers import DRIVERS, DriverType, execute_command


class TestDispatch:

    def test_execute_command_returns_error_for_unknown_driver(self):
        result = execute_command({"driver": "no-existe"}, "encender", {})
        assert result["ok"] is False and "no reconocido" in result["error"]

    def test_execute_command_delegates_to_corresponding_driver(self):
        with patch.object(DRIVERS[DriverType.TUYA], "execute",
                          return_value={"ok": True, "marker": "tuya"}) as mock_exec:
            result = execute_command({"driver": DriverType.TUYA}, "encender", {"foo": "bar"})
        assert result == {"ok": True, "marker": "tuya"}
        assert mock_exec.call_args[0][2] == {"foo": "bar"}
