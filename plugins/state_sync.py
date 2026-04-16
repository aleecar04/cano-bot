import requests
import logging
from typing import Dict, List
import time
from datetime import datetime

from plugins.device_cache import device_cache, DeviceState
from plugins._core import is_backend_reachable
from plugins.bot_config import BACKEND_URL, WEBHOOK_HEADERS as HEADERS

logger = logging.getLogger(__name__)


class StateSync:

    def __init__(self, max_retries: int = 3):
        self.pending_changes: Dict[str, DeviceState] = {}
        self.retry_queue: List[dict] = []
        self.max_retries = max_retries
        self.syncs_completed = 0
        self.syncs_failed = 0
        self.reconciliation_count = 0

    def mark_device_changed(self, device_id: str, state: DeviceState):
        """Marca un dispositivo con cambios pendientes de sincronizar."""
        self.pending_changes[device_id] = state
        logger.debug(f"Marcado para sincronizar: {device_id}")

    def sync_pending_changes(self):
        if not self.pending_changes or not is_backend_reachable():
            return

        changes_copy = self.pending_changes.copy()
        self.pending_changes.clear()

        for device_id, state in changes_copy.items():
            self._sync_one(device_id, state)

        self._process_retries()

    def _sync_one(self, device_id: str, state: DeviceState):
        """Intenta sincronizar un dispositivo. Si falla, lo encola para reintento."""
        try:
            self._patch_device_status(device_id, state)
            self.syncs_completed += 1
        except Exception as e:
            logger.error(f"Error sincronizando {device_id}: {e}")
            self._enqueue_retry(device_id, state)
            self.syncs_failed += 1

    def _patch_device_status(self, device_id: str, state: DeviceState):
        response = requests.patch(
            f"{BACKEND_URL}/api/v1/devices/{device_id}/status",
            json={
                "is_online": state.is_online,
                "estado": state.estado,
                "source": state.source,
                "confidence": state.confidence,
                "timestamp": datetime.fromtimestamp(state.last_update).isoformat(),
            },
            headers=HEADERS,
            timeout=5,
        )
        response.raise_for_status()
        logger.debug(f"Sincronizado {device_id}")

    def _enqueue_retry(self, device_id: str, state: DeviceState):
        """Encola un dispositivo para reintento con backoff exponencial."""
        self.retry_queue.append(
            {
                "device_id": device_id,
                "state": state,
                "retries": 0,
                "timestamp": time.time(),
            }
        )

    def _process_retries(self):
        if not self.retry_queue:
            return

        current_time = time.time()

        for item in self.retry_queue[:]:
            backoff = 2 ** item["retries"]
            time_since_last = current_time - item["timestamp"]

            if time_since_last < backoff:
                continue

            self._attempt_retry(item)

    def _attempt_retry(self, item: dict):
        """Intenta reenviar un item de la cola. Lo elimina si tiene exito o supera max_retries."""
        try:
            self._patch_device_status(item["device_id"], item["state"])
            self.retry_queue.remove(item)
            logger.info(f"Reintento exitoso: {item['device_id']}")
        except Exception:
            item["retries"] += 1
            if item["retries"] >= self.max_retries:
                logger.error(
                    f"Max retries alcanzado para {item['device_id']}, descartando"
                )
                self.retry_queue.remove(item)
            else:
                logger.warning(
                    f"Reintentando {item['device_id']} (intento {item['retries']})"
                )

    def full_reconciliation(self):
        """
        Compara el cache local con el backend.
        Si el backend tiene estado mas nuevo, actualiza el cache.
        """
        if not is_backend_reachable():
            return
        logger.debug("Iniciando reconciliacion completa...")

        for device_id, local_state in device_cache.get_all().items():
            self._reconcile_device(device_id, local_state)

        self.reconciliation_count += 1

    def _reconcile_device(self, device_id: str, local_state: DeviceState):
        try:
            backend_state = self._fetch_device_status(device_id)
            if self._backend_is_newer(backend_state, local_state):
                logger.info(f"Backend mas nuevo para {device_id}, actualizando cache")
                device_cache.update(
                    device_id,
                    backend_state.get("estado", {}),
                    backend_state.get("is_online", False),
                    source="backend",
                    confidence=1.0,
                )
        except Exception as e:
            logger.warning(f"Error en reconciliacion de {device_id}: {e}")

    def _fetch_device_status(self, device_id: str) -> dict:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/devices/{device_id}/status",
            headers=HEADERS,
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    def _backend_is_newer(self, backend_state: dict, local_state: DeviceState) -> bool:
        backend_time_str = backend_state.get("last_update")
        if not backend_time_str:
            return False
        try:
            backend_time = datetime.fromisoformat(backend_time_str).timestamp()
            return backend_time > local_state.last_update
        except (ValueError, TypeError):
            return False

    def get_stats(self) -> dict:
        return {
            "pending_changes": len(self.pending_changes),
            "retry_queue": len(self.retry_queue),
            "syncs_completed": self.syncs_completed,
            "syncs_failed": self.syncs_failed,
            "reconciliations": self.reconciliation_count,
        }


state_sync = StateSync()
