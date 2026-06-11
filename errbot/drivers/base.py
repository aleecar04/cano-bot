from abc import ABC, abstractmethod
from .actions_catalog import Action

_COLORES: dict[str, tuple[int, int, int]] = {
    "rojo":     (255, 0,   0),
    "verde":    (0,   200, 0),
    "azul":     (0,   0,   255),
    "amarillo": (255, 200, 0),
    "naranja":  (255, 100, 0),
    "morado":   (128, 0,   200),
    "violeta":  (148, 0,   211),
    "rosa":     (255, 20,  147),
    "cyan":     (0,   200, 255),
    "celeste":  (135, 206, 235),
    "blanco":   (255, 255, 255),
}


class BaseDriver(ABC):
    @abstractmethod
    def get_status(self, device: dict, timeout: float = 2.0) -> dict:
        pass

    @abstractmethod
    def turn_on(self, device: dict) -> dict: pass

    @abstractmethod
    def turn_off(self, device: dict) -> dict: pass

    def brightness(self, device: dict, value: int) -> dict:
        return {"ok": False, "error": "Este dispositivo no soporta brillo"}

    def color_temperature(self, device: dict, value: int) -> dict:
        return {"ok": False, "error": "Este dispositivo no soporta temperatura de color"}

    def set_color_rgb(self, device: dict, r: int, g: int, b: int) -> dict:
        return {"ok": False, "error": "Este dispositivo no soporta color RGB"}

    def set_volume(self, device: dict, value: int) -> dict:
        return {"ok": False, "error": "Este dispositivo no soporta volumen absoluto"}

    def open_app(self, device: dict, app: str) -> dict:
        return {"ok": False, "error": "Este dispositivo no soporta apertura de apps"}

    def _dispatch_color(self, device: dict, payload: dict) -> dict:
        if "color" in payload:
            name = str(payload["color"]).lower().strip()
            rgb = _COLORES.get(name)
            if not rgb:
                return {"ok": False, "error": f"Color '{name}' no reconocido. Colores disponibles: {', '.join(_COLORES)}"}
            return self.set_color_rgb(device, *rgb)
        r = int(payload.get("r", 255))
        g = int(payload.get("g", 0))
        b = int(payload.get("b", 0))
        return self.set_color_rgb(device, r, g, b)

    def execute(self, device: dict, action: str, payload: dict = {}) -> dict:
        actions = {
            Action.ENCENDER:          lambda: self.turn_on(device),
            Action.APAGAR:            lambda: self.turn_off(device),
            Action.BRILLO:            lambda: self.brightness(device, payload.get("value", 100)),
            Action.TEMPERATURA_COLOR: lambda: self.color_temperature(device, payload.get("value", 4000)),
            Action.COLOR_RGB:         lambda: self._dispatch_color(device, payload),
            Action.SET_VOLUMEN:       lambda: self.set_volume(device, int(payload.get("value", 50))),
            Action.ABRIR_APP:         lambda: self.open_app(device, str(payload.get("app", ""))),
        }
        fn = actions.get(action)
        if not fn:
            return {"ok": False, "error": f"Acción '{action}' no soportada"}
        try:
            return fn()
        except Exception as e:
            return {"ok": False, "error": str(e)}
