from api import _client


def resolve_in_house(jid: str) -> str | None:
    return _client.get("/api/v1/users/resolve", params={"jid": jid}).json().get("user_id")
