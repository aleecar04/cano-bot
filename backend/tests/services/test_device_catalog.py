import pytest

from app.services.device_catalog import device_catalog_service


class TestDeviceCatalog:

    @pytest.mark.parametrize("device_type, action, supported", [
        ("Luz", "brillo", True),
        ("Enchufe", "encender", True),
        ("Enchufe", "brillo", False),
        ("SmartTV", "set_volumen", True),
        ("Luz", "telepatear", False),
    ])
    def test_is_action_supported(self, device_type, action, supported):
        assert device_catalog_service.is_action_supported(device_type, action) is supported

    @pytest.mark.parametrize("action, payload, ok", [
        ("temperatura_color", {"value": 2700}, True),
        ("temperatura_color", {"value": 3000}, False),
        ("color_rgb", {"color": "AZUL"}, True),
        ("color_rgb", {"color": "salmon"}, False),
        ("brillo", {"value": 100}, True),
        ("brillo", {"value": 101}, False),
        ("brillo", {"value": "abc"}, False),
        ("set_volumen", {"value": 30}, True),
        ("set_volumen", {"value": 200}, False),
        ("encender", {}, True),
        ("mute", {}, True),
    ])
    def test_validate_payload(self, action, payload, ok):
        result = device_catalog_service.validate_payload(action, payload)
        assert (result is None) is ok
