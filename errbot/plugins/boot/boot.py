import time
import socket
import logging
import netifaces
from concurrent.futures import ThreadPoolExecutor
from errbot import BotPlugin, botcmd

from plugins.device_cache import device_cache
from api import is_backend_reachable
from api import devices as api_devices
from api import bot as api_bot
from drivers import DRIVERS

logger = logging.getLogger(__name__)

_POLL_INTERVAL_S         = 45
_DRIVER_TIMEOUT_S        = 2.0
_POLL_FUTURE_TIMEOUT_S   = 5     # cuánto esperamos a cada worker del ThreadPool
_PATCH_TIMEOUT_S         = 5     # timeout del PATCH HTTP al backend
_REACHABLE_PROBE_TIMEOUT = 1.5


class Boot(BotPlugin):
    """Plugin que arranca con Errbot: carga los devices de su casa (vía bot_token) y
    mantiene un único bucle de polling. La identidad de la casa la da el token, no hace
    falta identificarse contra el backend."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.devices: list[dict] = []
        self.executor = ThreadPoolExecutor(max_workers=10)

    def activate(self):
        super().activate()
        logger.info("Boot plugin activating...")
        try:
            self._reload_and_preload()
            self._send_heartbeat()
            self.start_poller(_POLL_INTERVAL_S, self.poll_all_devices)
            logger.info(f"Polling started (every {_POLL_INTERVAL_S} s)")
        except Exception:
            logger.exception("Error in Boot.activate")

    def deactivate(self):
        logger.info("Boot plugin deactivating...")
        try:
            self.stop_poller(self.poll_all_devices)
            self.executor.shutdown(wait=False)
        except Exception:
            logger.exception("Error stopping services")
        super().deactivate()


    def _reload_and_preload(self):
        """Refresca la lista de devices desde el backend y precarga el cache."""
        self.devices = self._fetch_devices_from_backend()
        for d in self.devices:
            device_cache.update(
                device_id=d["id"],
                state=d.get("state") or {},
                is_online=d.get("is_online", False),
            )

    def _fetch_devices_from_backend(self) -> list[dict]:
        if not is_backend_reachable():
            return self.devices
        try:
            data = api_devices.get_all()
            logger.info(f"Loaded {len(data)} devices from backend")
            return data
        except Exception:
            logger.exception("Failed to load devices")
            return self.devices

    def poll_all_devices(self):
        """Bucle único: comprueba red, refresca lista, sondea cada device en paralelo, sincroniza si cambió."""
        self._send_heartbeat()
        if not self._probe_home_network():
            logger.info("Sin acceso a la red local — saltando poll")
            return
        self.devices = self._fetch_devices_from_backend()
        if not self.devices:
            return
        self._poll_in_parallel()

    def _poll_in_parallel(self) -> None:
        start = time.time()
        futures = [self.executor.submit(self._poll_one, d) for d in self.devices]
        results: list[dict | None] = []
        for f in futures:
            try:
                results.append(f.result(timeout=_POLL_FUTURE_TIMEOUT_S))
            except Exception as e:
                logger.debug(f"Error waiting for poll result: {e}")
                results.append(None)
        online = sum(1 for r in results if r and r.get("is_online"))
        logger.info(f"Poll done in {time.time()-start:.2f}s — {online}/{len(self.devices)} online")

    def _poll_one(self, device: dict) -> dict | None:
        """Sondea un device. Si falla, lo marca offline. Si cambió, lo sincroniza."""
        driver = DRIVERS.get(device.get("driver"))
        if not driver:
            return None
        try:
            status = driver.get_status(device, timeout=_DRIVER_TIMEOUT_S)
        except Exception:
            logger.exception("Error polling %s", device.get("name"))
            self._sync_offline(device["id"])
            return None
        if status is None:
            return None
        self._sync_if_changed(device["id"], status)
        return status

    def _sync_if_changed(self, device_id: str, status: dict):
        current_online = status.get("is_online", False)
        current_state  = status.get("state") or {}
        old = device_cache.get(device_id)
        if old and old.is_online == current_online and old.state == current_state:
            return  # sin cambio, no toques al backend
        self._patch_backend(device_id, current_online, current_state)

    def _sync_offline(self, device_id: str):
        old = device_cache.get(device_id)
        if old and not old.is_online:
            return  # ya estaba offline
        current_state = old.state if old else {}
        self._patch_backend(device_id, is_online=False, state=current_state)

    def _patch_backend(self, device_id: str, is_online: bool, state: dict):
        """PATCH /devices/{id}/status. Actualiza el cache SOLO si el PATCH tiene éxito;
        así un fallo deja la cache vieja y el próximo poll lo reintentará."""
        if not is_backend_reachable():
            return
        try:
            api_devices.patch_status(device_id, is_online, state, timeout=_PATCH_TIMEOUT_S)
            device_cache.update(device_id, state=state, is_online=is_online)
        except Exception as e:
            logger.warning(f"PATCH /devices/{device_id}/status failed: {e}")


    def _send_heartbeat(self):
        """Avisa al backend de que el bot sigue vivo (estado online/offline)."""
        if not is_backend_reachable():
            return
        try:
            api_bot.heartbeat()
        except Exception as e:
            logger.debug(f"Heartbeat failed: {e}")

    def _probe_home_network(self) -> bool:
        """TCP connect al gateway por defecto. Devuelve True si el bot está en una red operativa."""
        try:
            gw_info = netifaces.gateways().get("default", {}).get(netifaces.AF_INET)
            if not gw_info:
                return False
            gw_ip = gw_info[0]
        except Exception:
            return False
        for port in (53, 80, 443):
            try:
                with socket.create_connection((gw_ip, port), timeout=_REACHABLE_PROBE_TIMEOUT):
                    return True
            except ConnectionRefusedError:
                # El gateway respondió con RST: está vivo aunque rechace el puerto.
                return True
            except OSError:
                continue
        return False

    @botcmd(hidden=True)
    def poll_device(self, msg, args):
        """Interno: sondea un único device por id (refresca lista si no lo conoce)."""
        device_id = args.strip()
        device = next((d for d in self.devices if d["id"] == device_id), None)
        if not device:
            self._reload_and_preload()
            device = next((d for d in self.devices if d["id"] == device_id), None)
        if device:
            self.executor.submit(self._poll_one, device)
        return ""
