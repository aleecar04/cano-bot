from api import _client


def get_all() -> list[dict]:
    return _client.get("/api/v1/devices/all").json()


def patch_status(device_id: str, is_online: bool, state: dict, timeout: float = 5) -> None:
    _client.patch(
        f"/api/v1/devices/{device_id}/status",
        json={"is_online": is_online, "state": state},
        timeout=timeout,
    )


def patch_config(device_id: str, config: dict, timeout: float = 3) -> None:
    _client.patch(f"/api/v1/devices/{device_id}/config", json=config, timeout=timeout)


def get_ha_credentials() -> dict:
    return _client.get("/api/v1/devices/ha/credentials").json()


def import_ha(user_id, states: list, entity_registry: list, device_registry: list) -> dict:
    return _client.post(
        "/api/v1/devices/ha/import",
        json={
            "user_id":         user_id,
            "states":          states,
            "entity_registry": entity_registry,
            "device_registry": device_registry,
        },
        timeout=15,
    ).json()
