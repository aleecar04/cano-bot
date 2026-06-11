import asyncio
import logging
import time
from aiowebostv import WebOsClient
from wakeonlan import send_magic_packet
from .base import BaseDriver
from .actions_catalog import Action
from api import devices as api_devices

logger = logging.getLogger(__name__)

LG_APPS = {
    "netflix": "netflix",
    "youtube": "youtube.leanback.v4",
    "prime":   "amazon",
}

class LGTVDriver(BaseDriver):
    async def _client(self, device: dict) -> WebOsClient:
        config = device.get("config") or {}
        client_key = config.get("client_key")
        client = WebOsClient(device["ip"], client_key=client_key)
        await client.connect()

        if client.client_key and client.client_key != client_key:
            try:
                await asyncio.to_thread(
                    api_devices.patch_config,
                    device["id"],
                    {**config, "client_key": client.client_key},
                )
            except Exception as e:
                logger.warning(f"No se pudo guardar client_key: {e}")

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
                "state": {"power": "on" if is_online else "off"}
            }
        except Exception as e:
            return {"is_online": False, "error": str(e)}

    def turn_on(self, device: dict) -> dict:
        mac = device.get("mac")
        if not mac:
            return {"ok": False, "error": "MAC no configurada para Wake on LAN"}
        try:
            send_magic_packet(mac)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def turn_off(self, device: dict) -> dict:
        try:
            async def _fn():
                c = await self._client(device)
                await c.power_off()
                await c.disconnect()
                return {"ok": True}
            return self._run(_fn())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_volume(self, device: dict, value: int) -> dict:
        try:
            async def _fn():
                c = await self._client(device)
                await c.set_volume(max(0, min(100, value)))
                await c.disconnect()
                return {"ok": True, "volume": value}
            return self._run(_fn())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def open_app(self, device: dict, app: str) -> dict:
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

    def execute(self, device: dict, action: str, payload: dict = {}) -> dict:
        extras = {
            Action.SUBIR_VOLUMEN: lambda: self._volume_step(device, "up"),
            Action.BAJAR_VOLUMEN: lambda: self._volume_step(device, "down"),
            Action.MUTE:          lambda: self.set_volume(device, 0),
            Action.SET_VOLUMEN:   lambda: self.set_volume(device, int(payload.get("value", 50))),
            Action.ABRIR_APP:     lambda: self.open_app(device, str(payload.get("app", ""))),
        }
        if action in extras:
            return extras[action]()
        return super().execute(device, action, payload)

    def _volume_step(self, device: dict, direction: str) -> dict:
        try:
            async def _fn():
                c = await self._client(device)
                if direction == "up":
                    await c.volume_up()
                else:
                    await c.volume_down()
                await c.disconnect()
                return {"ok": True}
            return self._run(_fn())
        except Exception as e:
            return {"ok": False, "error": str(e)}