from api import _client


def get_all() -> list[dict]:
    return _client.get("/api/v1/devices/all").json()


def patch_status(device_id: str, is_online: bool, estado: dict, timeout: float = 5) -> None:
    _client.patch(
        f"/api/v1/devices/{device_id}/status",
        json={"is_online": is_online, "estado": estado},
        timeout=timeout,
    )


def patch_config(device_id: str, config: dict, timeout: float = 3) -> None:
    _client.patch(f"/api/v1/devices/{device_id}/config", json=config, timeout=timeout)
