"""Tests unitarios para app/services/devices.py — lógica pura, sin Supabase."""
import pytest
from app.services.devices import inferir_driver, inferir_config


class TestInferirDriver:
    def test_luz_devuelve_tuya(self):
        assert inferir_driver("Luz") == "tuya"

    def test_iot_devuelve_tuya(self):
        assert inferir_driver("IoT") == "tuya"

    def test_termostato_devuelve_tuya(self):
        assert inferir_driver("Termostato") == "tuya"

    def test_light_devuelve_tuya(self):
        assert inferir_driver("light") == "tuya"

    def test_switch_devuelve_tuya(self):
        assert inferir_driver("switch") == "tuya"

    def test_climate_devuelve_tuya(self):
        assert inferir_driver("climate") == "tuya"

    def test_smarttv_lg_devuelve_lg_tv(self):
        assert inferir_driver("SmartTV", hostname="LG-TV-Salon") == "lg_tv"

    def test_smarttv_samsung_devuelve_samsung_tv(self):
        assert inferir_driver("SmartTV", hostname="Samsung-TV") == "samsung_tv"

    def test_smarttv_generico_devuelve_android_tv(self):
        assert inferir_driver("SmartTV", hostname="shield") == "android_tv"

    def test_altavoz_no_tiene_driver(self):
        # Altavoces (Alexa, Sonos) no son Tuya — no deben tener driver nativo
        assert inferir_driver("Altavoz") is None

    def test_camara_no_tiene_driver(self):
        assert inferir_driver("Camara") is None

    def test_ordenador_no_tiene_driver(self):
        assert inferir_driver("Ordenador") is None

    def test_tipo_desconocido_devuelve_none(self):
        assert inferir_driver("Nevera") is None

    def test_tipo_vacio_devuelve_none(self):
        assert inferir_driver("") is None


class TestInferirConfig:
    def test_luz_devuelve_channel(self):
        cfg = inferir_config("Luz")
        assert "channel" in cfg

    def test_iot_devuelve_channel(self):
        cfg = inferir_config("IoT")
        assert "channel" in cfg

    def test_smarttv_devuelve_dict_vacio(self):
        assert inferir_config("SmartTV") == {}

    def test_tipo_desconocido_devuelve_dict_vacio(self):
        assert inferir_config("Nevera") == {}
