from api import _client


def heartbeat(timeout: float = 3) -> None:
    """Avisa al backend de que el bot sigue vivo (estado online/offline)."""
    _client.post("/api/v1/bot/heartbeat", timeout=timeout)
