from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import pytest

from app.services import xmpp as xmpp_service


class TestCreateXmppAccount:

    def test_invoca_dos_comandos_add_user(self):
        async def run():
            with patch("app.services.xmpp.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock()
                mock_resp1 = MagicMock()
                mock_resp1.json.return_value = {"command": {"sessionid": "S1"}}
                mock_resp1.raise_for_status = MagicMock()
                mock_resp2 = MagicMock()
                mock_resp2.raise_for_status = MagicMock()
                mock_client.post.side_effect = [mock_resp1, mock_resp2]
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                pwd = await xmpp_service.create_xmpp_account("usr")
            assert isinstance(pwd, str)
            assert len(pwd) > 10
            # Dos POST: start + complete
            assert mock_client.post.await_count == 2
        asyncio.run(run())


class TestSendXmppMessage:

    def test_envia_y_devuelve_message_id(self):
        async def run():
            with patch("app.services.xmpp.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_resp = MagicMock()
                mock_resp.raise_for_status = MagicMock()
                mock_client.post = AsyncMock(return_value=mock_resp)
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                msg_id = await xmpp_service.send_xmpp_message(
                    body="hola",
                    from_jid="usr@xmpp",
                    xmpp_password="pwd",
                    to_jid="bot@xmpp/res",
                )
            assert isinstance(msg_id, str)
            assert len(msg_id) > 10  # uuid
        asyncio.run(run())

    def test_message_id_fijo_se_devuelve(self):
        async def run():
            with patch("app.services.xmpp.httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_resp = MagicMock()
                mock_resp.raise_for_status = MagicMock()
                mock_client.post = AsyncMock(return_value=mock_resp)
                mock_client_cls.return_value.__aenter__.return_value = mock_client
                msg_id = await xmpp_service.send_xmpp_message(
                    body="hola", from_jid="u@x", xmpp_password="p",
                    to_jid="bot@x", message_id="custom-id",
                )
            assert msg_id == "custom-id"
        asyncio.run(run())


@pytest.mark.parametrize("status_code, response_type, expected", [
    (200, "result", True),
    (200, "error", False),
])
def test_is_bot_online(status_code, response_type, expected):
    async def run():
        with patch("app.services.xmpp.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_resp = MagicMock(status_code=status_code)
            mock_resp.json.return_value = {"type": response_type}
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            assert await xmpp_service.is_bot_online("bot@x/res") is expected
    asyncio.run(run())


def test_is_bot_online_returns_false_on_exception():
    async def run():
        with patch("app.services.xmpp.httpx.AsyncClient",
                   side_effect=RuntimeError("network down")):
            assert await xmpp_service.is_bot_online("bot@x/res") is False
    asyncio.run(run())
