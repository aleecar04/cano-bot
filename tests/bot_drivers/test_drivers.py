"""Tests unitarios para los drivers de dispositivos."""
from unittest.mock import MagicMock, patch, call
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_device(driver="tuya", ip="192.168.1.100", **kwargs) -> dict:
    return {
        "id": "device-1",
        "ip": ip,
        "mac": "AA:BB:CC:DD:EE:FF",
        "driver": driver,
        "config": {},
        **kwargs,
    }


# ── HA Driver ─────────────────────────────────────────────────────────────────

class TestHADriver:
    def setup_method(self):
        from drivers.ha_driver import HomeAssistantDriver
        self.driver = HomeAssistantDriver()
        self.device = make_device(
            driver="homeassistant",
            ip="192.168.1.50",
            config={
                "ha_url": "http://192.168.1.50:8123",
                "token": "test-token",
                "entity_id": "light.salon",
            },
        )

    def test_encender_llama_al_servicio_correcto(self):
        with patch("drivers.ha_driver.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = lambda: None
            result = self.driver.encender(self.device)
        assert result["ok"] is True
        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        assert "light/turn_on" in url

    def test_apagar_llama_al_servicio_correcto(self):
        with patch("drivers.ha_driver.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = lambda: None
            result = self.driver.apagar(self.device)
        assert result["ok"] is True
        url = mock_post.call_args[0][0]
        assert "light/turn_off" in url

    def test_switch_usa_dominio_switch(self):
        device = make_device(
            driver="homeassistant",
            ip="192.168.1.50",
            config={
                "ha_url": "http://192.168.1.50:8123",
                "token": "test-token",
                "entity_id": "switch.cocina",
            },
        )
        with patch("drivers.ha_driver.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = lambda: None
            self.driver.encender(device)
        url = mock_post.call_args[0][0]
        assert "switch/turn_on" in url

    def test_brillo_llama_a_light_turn_on(self):
        with patch("drivers.ha_driver.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = lambda: None
            result = self.driver.brillo(self.device, 75)
        assert result["ok"] is True
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["brightness_pct"] == 75

    def test_get_status_online(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = lambda: None
        mock_response.json.return_value = {
            "state": "on",
            "attributes": {"brightness": 255},
        }
        with patch("drivers.ha_driver.requests.get", return_value=mock_response):
            result = self.driver.get_status(self.device)
        assert result["is_online"] is True
        assert result["estado"]["power"] is True

    def test_get_status_unavailable(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = lambda: None
        mock_response.json.return_value = {"state": "unavailable", "attributes": {}}
        with patch("drivers.ha_driver.requests.get", return_value=mock_response):
            result = self.driver.get_status(self.device)
        assert result["is_online"] is False

    def test_error_de_red_devuelve_is_online_false(self):
        import requests as req
        with patch("drivers.ha_driver.requests.get", side_effect=req.ConnectionError):
            result = self.driver.get_status(self.device)
        assert result["is_online"] is False

    def test_encender_fallo_de_red(self):
        import requests as req
        with patch("drivers.ha_driver.requests.post", side_effect=req.ConnectionError):
            result = self.driver.encender(self.device)
        assert result["ok"] is False
        assert "error" in result


# ── Android TV Driver ─────────────────────────────────────────────────────────

class TestAndroidTVDriver:
    def setup_method(self):
        from drivers.android_tv import AndroidTVDriver
        self.driver = AndroidTVDriver()
        self.device = make_device(driver="android_tv", ip="192.168.1.110")

    def _mock_adb(self):
        mock = MagicMock()
        mock.return_value = MagicMock(stdout="connected", returncode=0)
        return mock

    def test_encender_envia_keyevent_power(self):
        with patch("drivers.android_tv.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            self.driver.encender(self.device)
        calls_args = [str(c) for c in mock_run.call_args_list]
        assert any("26" in c for c in calls_args)

    def test_subir_volumen_envia_keyevent_24(self):
        with patch("drivers.android_tv.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            self.driver.ejecutar(self.device, "subir_volumen")
        calls_args = [str(c) for c in mock_run.call_args_list]
        assert any("24" in c for c in calls_args)

    def test_set_volumen_escala_a_15_pasos(self):
        with patch("drivers.android_tv.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            result = self.driver.set_volumen(self.device, 100)
        assert result["ok"] is True
        assert result["volumen"] == 15  # 100% → paso 15

    def test_set_volumen_cero(self):
        with patch("drivers.android_tv.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            result = self.driver.set_volumen(self.device, 0)
        assert result["volumen"] == 0

    def test_abrir_app_netflix(self):
        with patch("drivers.android_tv.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            result = self.driver.abrir_app(self.device, "netflix")
        assert result["ok"] is True
        calls_args = [str(c) for c in mock_run.call_args_list]
        assert any("com.netflix.ninja" in c for c in calls_args)

    def test_accion_no_soportada(self):
        result = self.driver.ejecutar(self.device, "volar")
        assert result["ok"] is False

    def test_ejecutar_set_volumen_via_payload(self):
        with patch("drivers.android_tv.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            result = self.driver.ejecutar(self.device, "set_volumen", {"valor": 50})
        assert result["ok"] is True


# ── LG TV Driver ──────────────────────────────────────────────────────────────

class TestLGTVDriver:
    def setup_method(self):
        from drivers.lg_tv import LGTVDriver
        self.driver = LGTVDriver()
        self.device = make_device(
            driver="lg_tv",
            ip="192.168.1.120",
            config={"client_key": None},
        )

    def _mock_client(self, mock_c=None):
        if mock_c is None:
            mock_c = MagicMock()
        return mock_c

    def test_encender_envia_wol(self):
        device = {**self.device, "mac": "AA:BB:CC:DD:EE:FF"}
        with patch("drivers.lg_tv.send_magic_packet") as mock_wol:
            result = self.driver.encender(device)
        assert result["ok"] is True
        mock_wol.assert_called_once_with("AA:BB:CC:DD:EE:FF")

    def test_encender_sin_mac_devuelve_error(self):
        device = {**self.device, "mac": None}
        result = self.driver.encender(device)
        assert result["ok"] is False

    def test_set_volumen_llama_webos(self):
        mock_c = MagicMock()
        with patch.object(self.driver, "_run") as mock_run, \
             patch.object(self.driver, "_client", return_value=mock_c):
            mock_run.return_value = {"ok": True, "volumen": 60}
            result = self.driver.set_volumen(self.device, 60)
        assert result["ok"] is True

    def test_abrir_app_netflix(self):
        with patch.object(self.driver, "_run") as mock_run:
            mock_run.return_value = {"ok": True, "app": "netflix"}
            result = self.driver.abrir_app(self.device, "netflix")
        assert result["ok"] is True

    def test_abrir_app_desconocida_usa_id_raw(self):
        with patch.object(self.driver, "_run") as mock_run:
            mock_run.return_value = {"ok": True, "app": "custom.app.id"}
            result = self.driver.abrir_app(self.device, "custom.app.id")
        assert result["ok"] is True
