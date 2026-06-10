import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.conftest import TEST_USER_ID

_CONV_ID = str(uuid.uuid4())


def test_new_conversation_uses_body_title(client: TestClient):
    with patch("app.api.routes.conversations.create_conversation") as mock_create:
        mock_create.return_value = {"id": _CONV_ID, "user_id": TEST_USER_ID, "title": "Mi chat"}
        res = client.post("/api/v1/conversations/", json={"title": "Mi chat"})
    assert res.status_code == 200
    assert res.json()["title"] == "Mi chat"
    mock_create.assert_called_once_with(TEST_USER_ID, title="Mi chat")


def test_new_conversation_falls_back_to_default_when_title_missing(client: TestClient):
    with patch("app.api.routes.conversations.create_conversation") as mock_create:
        mock_create.return_value = {"id": _CONV_ID, "user_id": TEST_USER_ID, "title": "Nueva conversación"}
        res = client.post("/api/v1/conversations/", json={})
    assert res.status_code == 200
    mock_create.assert_called_once_with(TEST_USER_ID, title="Nueva conversación")
