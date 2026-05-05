import requests
from .base import BaseDriver

class HomeAssistantDriver(BaseDriver):

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _api(self, device):
        cfg = device["config"]
        return cfg["ha_url"], cfg["token"], cfg["entity_id"]

    def _call_service(self, device, service: str, extra: dict = {}) -> dict:
        url, token, entity_id = self._api(device)
        try:
            r = requests.post(
                f"{url}/api/services/{service}",
                headers=self._headers(token),
                json={"entity_id": entity_id, **extra},
                timeout=5
            )
            r.raise_for_status()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_status(self, device, timeout=2.0):
        url, token, entity_id = self._api(device)
        try:
            r = requests.get(
                f"{url}/api/states/{entity_id}",
                headers=self._headers(token),
                timeout=timeout
            )
            r.raise_for_status()
            data = r.json()
            return {
                "is_online": data["state"] not in ("unavailable", "unknown"),
                "estado": {
                    "power":      data["state"] == "on",
                    "state":      data["state"],
                    "attributes": data.get("attributes", {})
                }
            }
        except Exception as e:
            return {"is_online": False, "error": str(e)}

    def encender(self, device):
        domain = device["config"]["entity_id"].split(".")[0]
        return self._call_service(device, f"{domain}/turn_on")

    def apagar(self, device):
        domain = device["config"]["entity_id"].split(".")[0]
        return self._call_service(device, f"{domain}/turn_off")

    def brillo(self, device, valor):
        return self._call_service(device, "light/turn_on", {"brightness_pct": valor})

    def temperatura_color(self, device, valor):
        return self._call_service(device, "light/turn_on", {"color_temp": valor})