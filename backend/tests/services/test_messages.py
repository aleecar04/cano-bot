import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.xmpp import BotWebhookPayload
from app.services import messages as msg_service


def _run(coro):
    return asyncio.run(coro)


class TestMessagesService:

    def test_require_bot_target_raises_or_returns_jid(self):
        with patch("app.services.messages.get_bot_target_for_user", return_value=None), \
             pytest.raises(HTTPException) as exc:
            msg_service._require_bot_target("user_anabel")
        assert exc.value.status_code == 400

        with patch("app.services.messages.get_bot_target_for_user", return_value="cano-bot@xmpp.cano-app.com"):
            assert msg_service._require_bot_target("user_anabel") == "cano-bot@xmpp.cano-app.com"

    def test_authenticate_gajim_sender_when_same_house(self):
        with patch("app.services.messages.xmpp_account_repository") as mock_x, \
             patch("app.services.messages.house_member_repository") as mock_h:
            mock_x.find_user_id_by_jid.return_value = "user_anabel"
            mock_h.find_house_id_by_user.return_value = "casa_demo"
            assert msg_service._authenticate_gajim_sender("anabel@xmpp.cano-app.com", "casa_demo") == "user_anabel"

    @pytest.mark.parametrize("body, expected", [
        ("!ayuda", {"intent": "ayuda"}),
        ("!inventado", None),
    ])
    def test_known_or_unknown_command_skips_ollama(self, body, expected):
        with patch("app.services.messages.classify_intent", new_callable=AsyncMock) as mock_o:
            result = _run(msg_service._classify(body))
        assert result == expected
        mock_o.assert_not_awaited()

    def test_natural_text_calls_ollama(self):
        with patch("app.services.messages.classify_intent",
                   new_callable=AsyncMock, return_value={"intent": "control_device"}) as mock_o:
            result = _run(msg_service._classify("enciende la luz"))
        assert result == {"intent": "control_device"}
        mock_o.assert_awaited_once()

    def test_device_not_found_message(self):
        assert "luz salón" in msg_service._device_not_found_message({"device": "luz salón"})
        assert "qué dispositivo" in msg_service._device_not_found_message({})

    def test_intent_none_resolves_with_message_id(self):
        resolve = self._fake_resolve()
        result = _run(msg_service._try_resolve_in_backend(None, "user_anabel", {"id": "msg_hola"}, resolve))
        assert result is True and resolve.calls[0][0] == "msg_hola"

    def test_non_resolvable_intent_returns_false(self):
        resolve = self._fake_resolve()
        result = _run(msg_service._try_resolve_in_backend(
            {"intent": "ayuda"}, "user_anabel", {"id": "msg_hola"}, resolve))
        assert result is False and resolve.calls == []

    @pytest.mark.parametrize("side_effect, expected_in_reply", [
        (msg_service._ValidationError("acción inválida"), "acción inválida"),
        (msg_service._DeviceNotFound(), "fantasma"),
    ])
    def test_control_device_failures_reply_with_message(self, side_effect, expected_in_reply):
        resolve = self._fake_resolve()
        with patch("app.services.messages._dispatch_device_from_nlp",
                   new_callable=AsyncMock, side_effect=side_effect):
            result = _run(msg_service._try_resolve_in_backend(
                {"intent": "control_device", "device": "fantasma"},
                "user_anabel", {"id": "msg_hola"}, resolve,
            ))
        assert result is True and expected_in_reply in resolve.calls[0][1]

    def test_control_device_success_does_not_call_resolve(self):
        resolve = self._fake_resolve()
        with patch("app.services.messages._dispatch_device_from_nlp", new_callable=AsyncMock):
            result = _run(msg_service._try_resolve_in_backend(
                {"intent": "control_device"}, "user_anabel", {"id": "msg_hola"}, resolve))
        assert result is True and resolve.calls == []

    def test_user_without_house_raises_device_not_found(self):
        with patch("app.services.messages.get_house_id_for_user", return_value=None), \
             pytest.raises(msg_service._DeviceNotFound):
            _run(msg_service._dispatch_device_from_nlp(
                {"action": "encender", "device": "luz"}, "user_anabel", "msg_hola"))

    def test_unknown_device_raises_device_not_found(self):
        with patch("app.services.messages.get_house_id_for_user", return_value="casa_demo"), \
             patch("app.services.messages.device_repository") as mock_d:
            mock_d.find_by_name_and_house.return_value = None
            with pytest.raises(msg_service._DeviceNotFound):
                _run(msg_service._dispatch_device_from_nlp(
                    {"action": "encender", "device": "fantasma"}, "user_anabel", "msg_hola"))

    @pytest.mark.parametrize("device_type, action, payload", [
        ("Enchufe", "brillo", {"value": 50}),
        ("Luz", "brillo", {"value": 200}),
    ])
    def test_invalid_action_or_payload_raises(self, device_type, action, payload):
        with patch("app.services.messages.get_house_id_for_user", return_value="casa_demo"), \
             patch("app.services.messages.device_repository") as mock_d:
            mock_d.find_by_name_and_house.return_value = {
                "id": "device_lampara", "name": device_type, "type": device_type,
            }
            with pytest.raises(msg_service._ValidationError):
                _run(msg_service._dispatch_device_from_nlp(
                    {"action": action, "device": device_type.lower(), "payload": payload},
                    "user_anabel", "msg_hola"))

    def test_forwards_to_bot_when_intent_not_resolvable(self):
        with patch("app.services.messages._verify_conversation"), \
             patch("app.services.messages._require_bot_target", return_value="cano-bot@xmpp.cano-app.com"), \
             patch("app.services.messages._create_message", return_value={"id": "msg_hola"}), \
             patch("app.services.messages._classify", new_callable=AsyncMock, return_value=None), \
             patch("app.services.messages._try_resolve_in_backend",
                   new_callable=AsyncMock, return_value=False), \
             patch("app.services.messages._forward_to_bot", new_callable=AsyncMock) as mock_fwd, \
             patch("app.services.messages._touch_conversation"):
            result = _run(msg_service.process_message("hola", "user_anabel", "conv_demo"))
        assert result == {"id": "msg_hola"}
        mock_fwd.assert_awaited_once()

    def test_process_message_skips_bot_when_resolved(self):
        with patch("app.services.messages._verify_conversation"), \
             patch("app.services.messages._require_bot_target", return_value="cano-bot@xmpp.cano-app.com"), \
             patch("app.services.messages._create_message", return_value={"id": "msg_hola"}), \
             patch("app.services.messages._classify", new_callable=AsyncMock), \
             patch("app.services.messages._try_resolve_in_backend",
                   new_callable=AsyncMock, return_value=True), \
             patch("app.services.messages._forward_to_bot", new_callable=AsyncMock) as mock_fwd, \
             patch("app.services.messages._touch_conversation"):
            _run(msg_service.process_message("hola", "user_anabel", "conv_demo"))
        mock_fwd.assert_not_called()

    def test_updates_existing_message_when_same_house(self):
        with patch("app.services.messages.message_repository") as mock_m, \
             patch("app.services.messages.conversation_repository") as mock_c, \
             patch("app.services.messages.house_member_repository") as mock_h, \
             patch("app.services.messages.supabase"):
            mock_m.find_by_id.return_value = {"id": "msg_hola", "conversation_id": "conv_demo"}
            mock_c.find_user_id_by_id.return_value = "user_anabel"
            mock_h.find_house_id_by_user.return_value = "casa_demo"
            msg_service.handle_webhook(self._payload(), "casa_demo")

    def test_message_from_other_house_raises_403(self):
        with patch("app.services.messages.message_repository") as mock_m, \
             patch("app.services.messages.conversation_repository") as mock_c, \
             patch("app.services.messages.house_member_repository") as mock_h:
            mock_m.find_by_id.return_value = {"id": "msg_hola", "conversation_id": "conv_demo"}
            mock_c.find_user_id_by_id.return_value = "user_anabel"
            mock_h.find_house_id_by_user.return_value = "otra_casa"
            with pytest.raises(HTTPException) as exc:
                msg_service.handle_webhook(self._payload(), "casa_demo")
            assert exc.value.status_code == 403

    def test_get_user_messages_returns_list_for_user_conversations(self):
        with patch("app.services.messages.conversation_repository") as mock_c, \
             patch("app.services.messages.message_repository") as mock_m:
            mock_c.find_ids_by_user.return_value = ["conv_demo"]
            mock_m.find_by_conversation_ids.return_value = [{"id": "msg_hola"}]
            assert msg_service.get_user_messages("user_anabel") == [{"id": "msg_hola"}]

    def _fake_resolve(self):
        calls = []
        async def _r(mid, text):
            calls.append((mid, text))
        _r.calls = calls
        return _r

    def _payload(self):
        return BotWebhookPayload(
            from_jid="anabel@xmpp.cano-app.com", body="hola", response="hi", message_id="msg_hola",
        )
