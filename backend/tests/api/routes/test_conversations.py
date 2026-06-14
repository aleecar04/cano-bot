import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.conftest import TEST_USER_ID

_CONV_ID = str(uuid.uuid4())


class TestConversationsRoutes:

    def test_new_conversation_uses_body_title(self, client: TestClient):
        from app.services.messages import messages_service
        with patch.object(messages_service, "create_conversation") as mock_create:
            mock_create.return_value = {"id": _CONV_ID, "user_id": TEST_USER_ID, "title": "Mi chat"}
            res = client.post("/api/v1/conversations/", json={"title": "Mi chat"})
        assert res.status_code == 200
        assert res.json()["title"] == "Mi chat"
        mock_create.assert_called_once_with(TEST_USER_ID, title="Mi chat")
