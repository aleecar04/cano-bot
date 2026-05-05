from abc import ABC, abstractmethod

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
        """Obtener estado del dispositivo. Retorna {is_online: bool, estado: dict} o None si timeout"""
        pass

    @abstractmethod
    def encender(self, device: dict) -> dict: pass

    @abstractmethod
    def apagar(self, device: dict) -> dict: pass

    def brillo(self, device: dict, valor: int) -> dict:
        return {"ok": False, "error": "Este dispositivo no soporta brillo"}

    def temperatura_color(self, device: dict, valor: int) -> dict:
        return {"ok": False, "error": "Este dispositivo no soporta temperatura de color"}

    def color_rgb(self, device: dict, r: int, g: int, b: int) -> dict:
        return {"ok": False, "error": "Este dispositivo no soporta color RGB"}

    def set_volumen(self, device: dict, valor: int) -> dict:
        return {"ok": False, "error": "Este dispositivo no soporta volumen absoluto"}

    def abrir_app(self, device: dict, app: str) -> dict:
        return {"ok": False, "error": "Este dispositivo no soporta apertura de apps"}

    def _dispatch_color(self, device: dict, payload: dict) -> dict:
        if "color" in payload:
            nombre = str(payload["color"]).lower().strip()
            rgb = _COLORES.get(nombre)
            if not rgb:
                return {"ok": False, "error": f"Color '{nombre}' no reconocido. Colores disponibles: {', '.join(_COLORES)}"}
            return self.color_rgb(device, *rgb)
        r = int(payload.get("r", 255))
        g = int(payload.get("g", 0))
        b = int(payload.get("b", 0))
        return self.color_rgb(device, r, g, b)

    def ejecutar(self, device: dict, accion: str, payload: dict = {}) -> dict:
        acciones = {
            "encender":          lambda: self.encender(device),
            "apagar":            lambda: self.apagar(device),
            "brillo":            lambda: self.brillo(device, payload.get("valor", 100)),
            "temperatura_color": lambda: self.temperatura_color(device, payload.get("valor", 4000)),
            "color_rgb":         lambda: self._dispatch_color(device, payload),
            "set_volumen":       lambda: self.set_volumen(device, int(payload.get("valor", 50))),
            "abrir_app":         lambda: self.abrir_app(device, str(payload.get("app", ""))),
        }
        fn = acciones.get(accion)
        if not fn:
            return {"ok": False, "error": f"Acción '{accion}' no soportada"}
        try:
            return fn()
        except Exception as e:
            return {"ok": False, "error": str(e)}