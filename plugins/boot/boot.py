import os
import time
import socket
import logging
import requests
import netifaces
from concurrent.futures import ThreadPoolExecutor
from errbot import BotPlugin, botcmd

from plugins.device_cache import device_cache
from plugins.state_sync import state_sync
from plugins._core import is_backend_reachable, consume_backend_recovery
from drivers import DRIVERS

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
WEBHOOK_HEADERS = {"X-Webhook-Token": os.getenv("WEBHOOK_SECRET", "")}

_WRONG_NETWORK_THRESHOLD = 3
_REACHABLE_PROBE_TIMEOUT = 1.5  # seconds


class Boot(BotPlugin):
    """Plugin that runs on Errbot startup."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.devices: list[dict] = []
        self.poll_times: list[float] = []
        self.consecutive_all_offline = 0
        self.executor = ThreadPoolExecutor(max_workers=10)

    def activate(self):
        super().activate()
        logger.info("Boot plugin activating...")

        try:
            self._register_bot()
            self._load_devices()
            self.start_poller(45, self.poll_all_devices)
            logger.info("Device polling started (every 45 s)")

            self.start_poller(5, state_sync.sync_pending_changes)
            logger.info("State sync started (every 5 s)")

            self.start_poller(120, state_sync.full_reconciliation)
            logger.info("Reconciliation started (every 120 s)")

            self.start_poller(300, self._reload_devices)
            logger.info("Device refresh started (every 300 s)")

        except Exception as e:
            logger.error(f"Error in Boot.activate: {e}", exc_info=True)

    def _register_bot(self):
        """Find this bot's house on startup. Read-only — house is created by the user."""
        bot_jid = os.getenv("BOT_USERNAME", "")
        if not bot_jid:
            logger.warning("BOT_USERNAME not set — skipping house identification")
            return
        if not is_backend_reachable():
            logger.warning("Backend unreachable — skipping house identification")
            return
        try:
            r = requests.post(
                f"{BACKEND_URL}/api/v1/houses/bot/identify",
                json={"bot_jid": bot_jid},
                headers=WEBHOOK_HEADERS,
                timeout=5,
            )
            data = r.json()
            if data.get("configured"):
                logger.info(f"Bot identified — house_id={data.get('house_id')}")
            else:
                logger.warning("Bot JID not yet assigned to any house — waiting for owner to configure the app")
        except Exception as e:
            logger.error(f"Error identifying bot house: {e}")

    def _load_devices(self):
        """Load device list from backend API (not from Supabase directly)."""
        if not is_backend_reachable():
            logger.warning("Backend unreachable at startup — device list is empty")
            self.devices = []
            return
        try:
            r = requests.get(
                f"{BACKEND_URL}/api/v1/devices/all",
                headers=WEBHOOK_HEADERS,
                timeout=10,
            )
            if r.status_code == 200:
                self.devices = r.json()
                logger.info(f"Loaded {len(self.devices)} devices from backend")
            else:
                logger.warning(f"Backend returned {r.status_code} for device list")
                self.devices = []
        except Exception as e:
            logger.error(f"Failed to load devices: {e}")
            self.devices = []

    def _reload_devices(self):
        """Periodic device list refresh — picks up newly linked devices."""
        self._load_devices()

    def poll_all_devices(self):
        if consume_backend_recovery():
            logger.info("Backend recovery detected — reloading device list")
            self._reload_devices()

        if not self.devices:
            return

        if self._on_wrong_network():
            logger.info(
                f"Skipping poll — bot appears to be off the home network "
                f"({self.consecutive_all_offline} consecutive full-offline cycles)"
            )
            return

        start = time.time()
        logger.info(f"Polling {len(self.devices)} devices...")

        futures = [self.executor.submit(self._fetch_single_device, d) for d in self.devices]
        results = []
        for f in futures:
            try:
                results.append(f.result(timeout=5))
            except Exception as e:
                logger.debug(f"Error waiting for poll result: {e}")
                results.append(None)

        online_count = sum(1 for r in results if r and r.get("is_online"))
        if online_count == 0 and len(self.devices) > 0:
            self.consecutive_all_offline += 1
        else:
            self.consecutive_all_offline = 0

        elapsed = time.time() - start
        self.poll_times.append(elapsed)
        recent = self.poll_times[-10:]
        avg = sum(recent) / len(recent)
        logger.info(
            f"Poll done in {elapsed:.2f}s (avg last 10: {avg:.2f}s) — "
            f"{online_count}/{len(self.devices)} online"
        )

    def _on_wrong_network(self) -> bool:
        if self.consecutive_all_offline >= _WRONG_NETWORK_THRESHOLD:
            if not self._probe_home_network():
                return True
            self.consecutive_all_offline = 0
        return False

    def _probe_home_network(self) -> bool:
        try:
            gw_info = netifaces.gateways().get("default", {}).get(netifaces.AF_INET)
            if not gw_info:
                return False
            gw_ip = gw_info[0]
        except Exception:
            return False

        for port in [53, 80, 443]:
            try:
                with socket.create_connection((gw_ip, port), timeout=_REACHABLE_PROBE_TIMEOUT):
                    return True
            except ConnectionRefusedError:
                return True  # el gateway rechazó el puerto → está ahí, estamos en red
            except OSError:
                continue
        return False

    def _fetch_single_device(self, device: dict) -> dict | None:
        driver_type = device.get("driver")
        if not driver_type:
            return None
        driver = DRIVERS.get(driver_type)
        if not driver:
            logger.debug(f"Unknown driver '{driver_type}' for {device.get('name')}")
            return None
        try:
            status = driver.get_status(device, timeout=2.0)
        except Exception as e:
            logger.error(f"Error polling {device.get('name')}: {e}")
            device_cache.mark_offline(device["id"])
            return None

        if status is None:
            logger.debug(f"Timeout polling {device.get('name')}")
            return None

        old = device_cache.get(device["id"])
        new_is_online = status.get("is_online", False)
        new_estado = status.get("estado", {})

        new_state = device_cache.update(
            device_id=device["id"],
            estado=new_estado,
            is_online=new_is_online,
            source="poll",
            confidence=1.0,
        )

        # Only push to backend when something actually changed
        state_changed = (
            old is None
            or old.is_online != new_is_online
            or old.estado != new_estado
        )
        if state_changed:
            state_sync.mark_device_changed(device["id"], new_state)

        return status

    @botcmd(hidden=True)
    def poll_device(self, msg, args):
        """Internal: immediately poll a single device by id."""
        device_id = args.strip()
        device = next((d for d in self.devices if d["id"] == device_id), None)
        if not device:
            self._reload_devices()
            device = next((d for d in self.devices if d["id"] == device_id), None)
        if device:
            self.executor.submit(self._fetch_single_device, device)
        return ""

    def deactivate(self):
        logger.info("Boot plugin deactivating...")
        try:
            self.stop_poller(self.poll_all_devices)
            self.stop_poller(state_sync.sync_pending_changes)
            self.stop_poller(state_sync.full_reconciliation)
            self.stop_poller(self._reload_devices)
            self.executor.shutdown(wait=False)
        except Exception as e:
            logger.error(f"Error stopping services: {e}", exc_info=True)
        super().deactivate()
