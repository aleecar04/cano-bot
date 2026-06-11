from api import _client


def patch_result(command_id: str, error: str | None, result_data: dict | None = None) -> None:
    """Marca comando como ejecutado o fallido"""
    _client.patch(
        f"/api/v1/commands/{command_id}",
        json={"error": error, "result_data": result_data},
        timeout=3,
    )


def register_from_bot(
    *,
    user_id: str | None,
    device_id: str | None,
    action: str | None,
    payload: dict,
    error: str | None,
    message_id: str | None,
    result_data: dict | None = None,
) -> dict:
    return _client.post(
        "/api/v1/commands/from-bot",
        json={
            "user_id":     user_id,
            "device_id":   device_id,
            "action":      action,
            "payload":     payload,
            "error":       error,
            "message_id":  message_id,
            "result_data": result_data,
        },
        timeout=3,
    ).json()


def register_pending_from_bot(
    *,
    user_id: str | None,
    device_id: str | None,
    action: str | None,
    payload: dict,
    message_id: str | None,
) -> dict:
    return _client.post(
        "/api/v1/commands/from-bot",
        json={
            "user_id":     user_id,
            "device_id":   device_id,
            "action":      action,
            "payload":     payload,
            "message_id":  message_id,
            "pending":     True,
        },
        timeout=3,
    ).json()
