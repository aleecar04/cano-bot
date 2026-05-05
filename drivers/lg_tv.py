import asyncio
import os
import time
import requests
from aiowebostv import WebOsClient
from wakeonlan import send_magic_packet
from .base import BaseDriver

LG_APPS = {
    "netflix":  "netflix",
    "youtube":  "youtube.leanback.v4",
    "prime":    "amazon",
    "disney":   "disney",
    "spotify":  "spotify-beehiveapp",
    "hbo":      "hbo",
}

class LGTVDriver(BaseDriver):
    async def _client(self, device: dict) -> WebOsClient:
        config = device.get("config") or {}
        client_key = config.get("client_key")
        client = WebOsClient(device["ip"], client_key=client_key)
        await client.connect()

        if client.client_key and client.client_key != client_key:
            try:
                backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
                await asyncio.to_thread(
                    requests.patch,
                    f"{backend_url}/api/v1/devices/{device['id']}/config",
                    json={**config, "client_key": client.client_key},
                    headers={"X-Webhook-Token": os.getenv("WEBHOOK_SECRET")},
                    timeout=3,
                )
            except Exception as e:
                print(f"[WARN] No se pudo guardar client_key: {e}")

        return client

    def _run(self, coro):
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(asyncio.run, coro)
                        return future.result()
                else:
                    return loop.run_until_complete(coro)
            except RuntimeError:
                return asyncio.run(coro)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_status(self, device: dict, timeout: float = 2.0) -> dict:
        try:
            start_time = time.time()

            async def _fn():
                c = await self._client(device)
                power_state = await c.get_power_state()
                await c.disconnect()
                return power_state

            result = self._run(_fn())

            if time.time() - start_time > timeout:
                return {"is_online": False}

            if isinstance(result, dict) and "ok" in result and not result["ok"]:
                return {"is_online": False, "error": result.get("error")}

            state_str = (result or {}).get("state", "") if isinstance(result, dict) else ""
            is_online = state_str in ("Active", "Screen On", "Screen Saver")

            return {
                "is_online": is_online,
                "estado": {"power": "on" if is_online else "off"}
            }
        except Exception as e:
            return {"is_online": False, "error": str(e)}

    def encender(self, device: dict) -> dict:
        mac = device.get("mac")
        if not mac:
            return {"ok": False, "error": "MAC no configurada para Wake on LAN"}
        try:
            send_magic_packet(mac)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def apagar(self, device: dict) -> dict:
        try:
            async def _fn():
                c = await self._client(device)
                await c.power_off()
                await c.disconnect()
                return {"ok": True}
            return self._run(_fn())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_volumen(self, device: dict, valor: int) -> dict:
        try:
            async def _fn():
                c = await self._client(device)
                await c.set_volume(max(0, min(100, valor)))
                await c.disconnect()
                return {"ok": True, "volumen": valor}
            return self._run(_fn())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def abrir_app(self, device: dict, app: str) -> dict:
        app_id = LG_APPS.get(app.lower(), app)
        try:
            async def _fn():
                c = await self._client(device)
                await c.launch_app(app_id)
                await c.disconnect()
                return {"ok": True, "app": app}
            return self._run(_fn())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def ejecutar(self, device: dict, accion: str, payload: dict = {}) -> dict:
        extras = {
            "subir_volumen": lambda: self._volumen(device, "up"),
            "bajar_volumen": lambda: self._volumen(device, "down"),
            "mute":          lambda: self._mute(device),
            "set_volumen":   lambda: self.set_volumen(device, int(payload.get("valor", 50))),
            "abrir_app":     lambda: self.abrir_app(device, str(payload.get("app", ""))),
        }
        if accion in extras:
            return extras[accion]()
        return super().ejecutar(device, accion, payload)

    def _volumen(self, device: dict, direccion: str) -> dict:
        try:
            async def _fn():
                c = await self._client(device)
                if direccion == "up":
                    await c.volume_up()
                else:
                    await c.volume_down()
                await c.disconnect()
                return {"ok": True}
            return self._run(_fn())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mute(self, device: dict) -> dict:
        try:
            async def _fn():
                c      = await self._client(device)
                status = await c.get_volume()
                await c.set_mute(not status["muted"])
                await c.disconnect()
                return {"ok": True}
            return self._run(_fn())
        except Exception as e:
            return {"ok": False, "error": str(e)}