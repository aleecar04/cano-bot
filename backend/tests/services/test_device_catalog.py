from app.services.device_catalog import is_action_supported, validate_payload, Action


# ── is_action_supported ──────────────────────────────────────────────────────

class TestIsActionSupported:

    def test_luz_soporta_brillo(self):
        assert is_action_supported("Luz", "brillo") is True

    def test_enchufe_solo_encender_apagar(self):
        assert is_action_supported("Enchufe", "encender") is True
        assert is_action_supported("Enchufe", "brillo") is False

    def test_smarttv_soporta_volumen_y_app(self):
        assert is_action_supported("SmartTV", "set_volumen") is True
        assert is_action_supported("SmartTV", "abrir_app") is True

    def test_tipo_HA_se_mapea_a_categoria(self):
        assert is_action_supported("light", "brillo") is True
        assert is_action_supported("switch", "encender") is True
        assert is_action_supported("media_player", "subir_volumen") is True

    def test_tipo_desconocido_devuelve_false(self):
        assert is_action_supported("OnirixDevice", "encender") is False

    def test_accion_no_existente_devuelve_false(self):
        assert is_action_supported("Luz", "telepatear") is False


# ── validate_payload ────────────────────────────────────────────────────────

class TestValidatePayload:

    def test_temperatura_color_preset_valido(self):
        assert validate_payload("temperatura_color", {"valor": 2700}) is None
        assert validate_payload("temperatura_color", {"valor": 4000}) is None
        assert validate_payload("temperatura_color", {"valor": 6500}) is None

    def test_temperatura_color_no_preset_devuelve_error(self):
        result = validate_payload("temperatura_color", {"valor": 3000})
        assert result is not None
        assert "temperaturas" in result.lower()

    def test_temperatura_color_sin_valor_devuelve_error(self):
        assert validate_payload("temperatura_color", {}) is not None

    def test_color_rgb_color_conocido(self):
        assert validate_payload("color_rgb", {"color": "rojo"}) is None
        assert validate_payload("color_rgb", {"color": "AZUL"}) is None  # case-insensitive

    def test_color_rgb_desconocido_devuelve_error(self):
        result = validate_payload("color_rgb", {"color": "salmon"})
        assert result is not None
        assert "color" in result.lower()

    def test_brillo_valor_valido(self):
        assert validate_payload("brillo", {"valor": 0}) is None
        assert validate_payload("brillo", {"valor": 50}) is None
        assert validate_payload("brillo", {"valor": 100}) is None

    def test_brillo_fuera_de_rango(self):
        assert validate_payload("brillo", {"valor": -1}) is not None
        assert validate_payload("brillo", {"valor": 101}) is not None

    def test_brillo_valor_no_numerico(self):
        assert validate_payload("brillo", {"valor": "abc"}) is not None

    def test_set_volumen_valido(self):
        assert validate_payload("set_volumen", {"valor": 30}) is None

    def test_set_volumen_fuera_de_rango(self):
        assert validate_payload("set_volumen", {"valor": 200}) is not None

    def test_otras_acciones_pasan_validacion(self):
        """Acciones sin payload validable: encender, apagar, mute, etc."""
        assert validate_payload("encender", {}) is None
        assert validate_payload("apagar", {}) is None
        assert validate_payload("mute", {}) is None


class TestActionEnum:

    def test_action_values_son_strings_minusculas(self):
        for a in Action:
            assert a.value.islower()

    def test_action_se_compara_con_string(self):
        assert Action.ENCENDER == "encender"
        assert Action.COLOR_RGB == "color_rgb"
