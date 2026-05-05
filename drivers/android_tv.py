import subprocess
import time
from .base import BaseDriver

KEYCODES = {
    "encender":      "26",
    "apagar":        "26",
    "subir_volumen": "24",
    "bajar_volumen": "25",
    "mute":          "164",
    "home":          "3",
    "atras":         "4",
}

ANDROID_APPS = {
    "netflix":  "com.netflix.ninja",
    "youtube":  "com.google.android.youtube.tv",
    "prime":    "com.amazon.amazonvideo.livingroom",
    "disney":   "com.disney.disneyplus",
    "spotify":  "com.spotify.tv.android",
    "hbo":      "com.hbo.hbonow",
}

class AndroidTVDriver(BaseDriver):
    def _adb(self, ip: str, keycode: str, timeout: float = 2.0):
        try:
            subprocess.run(["adb", "connect", ip], capture_output=True, timeout=timeout)
            subprocess.run(
                ["adb", "-s", ip, "shell", "input", "keyevent", keycode],
                capture_output=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"ADB timeout {ip}")

    def get_status(self, device: dict, timeout: float = 2.0) -> dict:
        """Obtener estado del Android TV"""
        try:
            start_time = time.time()
            
            # Intentar conectar via ADB
            result = subprocess.run(
                ["adb", "connect", device["ip"]],
                capture_output=True,
                timeout=timeout,
                text=True
            )
            
            if time.time() - start_time > timeout:
                return None  # Timeout - no actualizar
            
            is_connected = "connected" in result.stdout
            return {
                "is_online": is_connected,
                "estado": {"device": device["ip"], "ultimo_update": time.time()}
            }
        except subprocess.TimeoutExpired:
            return None  # Timeout - no actualizar
        except Exception as e:
            return {"is_online": False, "error": str(e)}

    def encender(self, device: dict) -> dict:
        self._adb(device["ip"], KEYCODES["encender"])
        return {"ok": True}

    def apagar(self, device: dict) -> dict:
        self._adb(device["ip"], KEYCODES["apagar"])
        return {"ok": True}

    def set_volumen(self, device: dict, valor: int) -> dict:
        # Android TV STREAM_MUSIC max is typically 15 steps
        nivel = max(0, min(15, round(valor / 100 * 15)))
        ip = device["ip"]
        try:
            subprocess.run(["adb", "connect", ip], capture_output=True, timeout=3)
            subprocess.run(
                ["adb", "-s", ip, "shell", "media", "volume",
                 "--stream", "3", "--set", str(nivel)],
                capture_output=True, timeout=3
            )
            return {"ok": True, "volumen": nivel}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def abrir_app(self, device: dict, app: str) -> dict:
        package = ANDROID_APPS.get(app.lower(), app)
        ip = device["ip"]
        try:
            subprocess.run(["adb", "connect", ip], capture_output=True, timeout=3)
            subprocess.run(
                ["adb", "-s", ip, "shell", "monkey", "-p", package,
                 "-c", "android.intent.category.LAUNCHER", "1"],
                capture_output=True, timeout=5
            )
            return {"ok": True, "app": app}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def ejecutar(self, device: dict, accion: str, payload: dict = {}) -> dict:
        if accion == "set_volumen":
            return self.set_volumen(device, int(payload.get("valor", 50)))
        if accion == "abrir_app":
            return self.abrir_app(device, str(payload.get("app", "")))
        if accion in KEYCODES:
            self._adb(device["ip"], KEYCODES[accion])
            return {"ok": True}
        return {"ok": False, "error": f"Acción '{accion}' no soportada"}