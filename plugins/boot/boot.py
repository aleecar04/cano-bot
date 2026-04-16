import os
import time
import socket
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
from errbot import BotPlugin

from plugins.device_cache import device_cache
from plugins.state_sync import state_sync
from plugins._core import is_backend_reachable
from drivers import lg_tv, tuya_driver, android_tv, ha_driver

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
        self.drivers = {
            "lg_tv": lg_tv.LGTVDriver(),
            "tuya_driver": tuya_driver.TuyaDriver(),
            "android_tv": android_tv.AndroidTVDriver(),
            "homeassistant": ha_driver.HomeAssistantDriver(),
        }

    def activate(self):
        super().activate()
        logger.info("Boot plugin activating...")

        try:
            self._load_devices()
            self.start_poller(45, self.poll_all_devices)
            logger.info("Device polling started (every 45 s)")

            self.start_poller(30, state_sync.sync_pending_changes)
            logger.info("State sync started (every 30 s)")

            self.start_poller(120, state_sync.full_reconciliation)
            logger.info("Reconciliation started (every 120 s)")

            self.start_poller(300, self._reload_devices)
            logger.info("Device refresh started (every 300 s)")

        except Exception as e:
            logger.error(f"Error in Boot.activate: {e}", exc_info=True)

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
            if not self._probe_any_device():
                return True
            self.consecutive_all_offline = 0
        return False

    def _probe_any_device(self) -> bool:
        for device in self.devices[:5]:
            ip = device.get("ip")
            if not ip:
                continue
            for port in (80, 443, 8080):
                try:
                    with socket.create_connection((ip, port), timeout=_REACHABLE_PROBE_TIMEOUT):
                        return True
                except OSError:
                    continue
        return False

    def _fetch_single_device(self, device: dict) -> dict | None:
        driver_type = device.get("driver")
        if not driver_type:
            return None
        driver = self.drivers.get(driver_type)
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

        device_cache.update(
            device_id=device["id"],
            estado=status.get("estado", {}),
            is_online=status.get("is_online", False),
            source="poll",
            confidence=1.0,
        )
        return status

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
