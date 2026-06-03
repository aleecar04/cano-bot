from app.services.command_kinds import (
    INFO_ACTIONS,
    SYSTEM_ACTIONS,
    PREFIX_ACTIONS,
    classify_action_type,
    lookup_prefix_command,
)


class TestClassifyActionType:

    def test_info_actions(self):
        for a in INFO_ACTIONS:
            assert classify_action_type(a) == "info"

    def test_system_actions(self):
        for a in SYSTEM_ACTIONS:
            assert classify_action_type(a) == "system"

    def test_unknown_action_default_a_device(self):
        assert classify_action_type("encender") == "device"
        assert classify_action_type("foo") == "device"

    def test_none_default_a_device(self):
        assert classify_action_type(None) == "device"


class TestLookupPrefixCommand:

    def test_no_es_prefix_devuelve_none(self):
        assert lookup_prefix_command("hola") is None
        assert lookup_prefix_command("") is None

    def test_solo_exclamacion_devuelve_none(self):
        assert lookup_prefix_command("!") is None

    def test_comando_info_conocido(self):
        assert lookup_prefix_command("!ayuda") == {"intent": "ayuda"}
        assert lookup_prefix_command("!saludo") == {"intent": "saludo"}

    def test_comando_system_conocido(self):
        assert lookup_prefix_command("!scan_devices") == {"intent": "scan_devices"}
        assert lookup_prefix_command("!list_devices") == {"intent": "list_devices"}

    def test_comando_desconocido_devuelve_none(self):
        assert lookup_prefix_command("!inventado") is None

    def test_acciones_con_dispositivo(self):
        assert lookup_prefix_command("!acciones luz salon") == {
            "intent": "acciones", "dispositivo": "luz salon",
        }

    def test_acciones_sin_dispositivo(self):
        assert lookup_prefix_command("!acciones") == {"intent": "acciones"}


class TestPrefixActions:

    def test_prefix_actions_es_union(self):
        assert PREFIX_ACTIONS == INFO_ACTIONS | SYSTEM_ACTIONS
