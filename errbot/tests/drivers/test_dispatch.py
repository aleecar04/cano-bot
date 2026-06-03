from unittest.mock import patch, MagicMock


# ── DriverType enum ──────────────────────────────────────────────────────────

class TestDriverType:

    def test_valores_enum(self):
        from drivers import DriverType
        assert DriverType.TUYA == "tuya"
        assert DriverType.LG_TV == "lg_tv"
        assert DriverType.SAMSUNG_TV == "samsung_tv"
        assert DriverType.HOMEASSISTANT == "homeassistant"
        assert DriverType.GENERIC == "generic"


# ── ejecutar_comando ─────────────────────────────────────────────────────────

class TestEjecutarComando:

    def test_driver_desconocido_devuelve_error(self):
        from drivers import ejecutar_comando
        result = ejecutar_comando({"driver": "no-existe"}, "encender", {})
        assert result["ok"] is False
        assert "no reconocido" in result["error"]

    def test_driver_generic_devuelve_error(self):
        from drivers import ejecutar_comando, DriverType
        result = ejecutar_comando({"driver": DriverType.GENERIC}, "encender", {})
        assert result["ok"] is False

    def test_payload_none_se_normaliza_a_dict(self):
        """ejecutar_comando con payload=None no debe petar."""
        from drivers import ejecutar_comando, DRIVERS, DriverType
        with patch.object(DRIVERS[DriverType.TUYA], "ejecutar") as mock_exec:
            mock_exec.return_value = {"ok": True}
            ejecutar_comando({"driver": DriverType.TUYA}, "encender", None)
        assert mock_exec.call_args[0][2] == {}

    def test_delega_al_driver_correspondiente(self):
        from drivers import ejecutar_comando, DRIVERS, DriverType
        with patch.object(DRIVERS[DriverType.TUYA], "ejecutar") as mock_exec:
            mock_exec.return_value = {"ok": True, "marker": "tuya"}
            result = ejecutar_comando(
                {"driver": DriverType.TUYA}, "encender", {"foo": "bar"}
            )
        assert result == {"ok": True, "marker": "tuya"}
