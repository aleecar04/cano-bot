import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.services import messages as msg_service


def _run(coro):
    return asyncio.run(coro)


# ── _require_bot_target ──────────────────────────────────────────────────────

def test_require_bot_target_raises_400_when_missing_or_returns_jid():
    with patch("app.services.messages.get_bot_target_for_user", return_value=None), \
         pytest.raises(HTTPException) as exc:
        msg_service._require_bot_target("u1")
    assert exc.value.status_code == 400

    with patch("app.services.messages.get_bot_target_for_user", return_value="bot@x"):
        assert msg_service._require_bot_target("u1") == "bot@x"


# ── _authenticate_gajim_sender ──────────────────────────────────────────────

class TestAuthenticateGajimSender:

    def test_returns_user_id_when_member_of_same_house(self):
        with patch("app.services.messages.xmpp_account_repository") as mock_x, \
             patch("app.services.messages.house_member_repository") as mock_h:
            mock_x.find_user_id_by_jid.return_value = "u1"
            mock_h.find_house_id_by_user.return_value = "h1"
            assert msg_service._authenticate_gajim_sender("u@x/res", "h1") == "u1"


# ── _classify ───────────────────────────────────────────────────────────────

class TestClassify:

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


# ── _device_not_found_message ───────────────────────────────────────────────

def test_device_not_found_message():
    assert "luz salón" in msg_service._device_not_found_message({"dispositivo": "luz salón"})
    assert "qué dispositivo" in msg_service._device_not_found_message({})


# ── _try_resolve_in_backend ─────────────────────────────────────────────────

class TestTryResolveInBackend:

    def _fake_resolve(self):
        calls = []
        async def _r(mid, text):
            calls.append((mid, text))
        _r.calls = calls
        return _r

    def test_intent_none_resolves_with_message_id(self):
        resolve = self._fake_resolve()
        result = _run(msg_service._try_resolve_in_backend(None, "u1", {"id": "m1"}, resolve))
        assert result is True and resolve.calls[0][0] == "m1"

    def test_non_resolvable_intent_returns_false(self):
        resolve = self._fake_resolve()
        result = _run(msg_service._try_resolve_in_backend(
            {"intent": "ayuda"}, "u1", {"id": "m1"}, resolve))
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
                {"intent": "control_device", "dispositivo": "fantasma"},
                "u1", {"id": "m1"}, resolve,
            ))
        assert result is True and expected_in_reply in resolve.calls[0][1]

    def test_control_device_success_does_not_call_resolve(self):
        resolve = self._fake_resolve()
        with patch("app.services.messages._dispatch_device_from_nlp", new_callable=AsyncMock):
            result = _run(msg_service._try_resolve_in_backend(
                {"intent": "control_device"}, "u1", {"id": "m1"}, resolve))
        assert result is True and resolve.calls == []


# ── _dispatch_device_from_nlp ───────────────────────────────────────────────

class TestDispatchDeviceFromNlp:

    def test_user_without_house_raises_device_not_found(self):
        with patch("app.services.messages.get_house_id_for_user", return_value=None), \
             pytest.raises(msg_service._DeviceNotFound):
            _run(msg_service._dispatch_device_from_nlp(
                {"accion": "encender", "dispositivo": "luz"}, "u1", "m1"))

    def test_unknown_device_raises_device_not_found(self):
        with patch("app.services.messages.get_house_id_for_user", return_value="h1"), \
             patch("app.services.messages.device_repository") as mock_d:
            mock_d.find_by_name_and_house.return_value = None
            with pytest.raises(msg_service._DeviceNotFound):
                _run(msg_service._dispatch_device_from_nlp(
                    {"accion": "encender", "dispositivo": "fantasma"}, "u1", "m1"))

    @pytest.mark.parametrize("device_type, action, payload", [
        ("Enchufe", "brillo", {"valor": 50}),
        ("Luz", "brillo", {"valor": 200}),
    ])
    def test_invalid_action_or_payload_raises(self, device_type, action, payload):
        with patch("app.services.messages.get_house_id_for_user", return_value="h1"), \
             patch("app.services.messages.device_repository") as mock_d:
            mock_d.find_by_name_and_house.return_value = {
                "id": "d1", "name": device_type, "type": device_type,
            }
            with pytest.raises(msg_service._ValidationError):
                _run(msg_service._dispatch_device_from_nlp(
                    {"accion": action, "dispositivo": device_type.lower(), "payload": payload},
                    "u1", "m1"))


# ── handle_webhook ──────────────────────────────────────────────────────────

class TestProcessMessage:

    def test_forwards_to_bot_when_intent_not_resolvable(self):
        with patch("app.services.messages._verify_conversation"), \
             patch("app.services.messages._require_bot_target", return_value="bot@x"), \
             patch("app.services.messages._create_message", return_value={"id": "m1"}), \
             patch("app.services.messages._classify", new_callable=AsyncMock, return_value=None), \
             patch("app.services.messages._try_resolve_in_backend",
                   new_callable=AsyncMock, return_value=False), \
             patch("app.services.messages._forward_to_bot", new_callable=AsyncMock) as mock_fwd, \
             patch("app.services.messages._touch_conversation"):
            result = _run(msg_service.process_message("hola", "u1", "c1"))
        assert result == {"id": "m1"}
        mock_fwd.assert_awaited_once()

    def test_process_message_short_circuits_when_resolved(self):
        with patch("app.services.messages._verify_conversation"), \
             patch("app.services.messages._require_bot_target", return_value="bot@x"), \
             patch("app.services.messages._create_message", return_value={"id": "m1"}), \
             patch("app.services.messages._classify", new_callable=AsyncMock), \
             patch("app.services.messages._try_resolve_in_backend",
                   new_callable=AsyncMock, return_value=True), \
             patch("app.services.messages._forward_to_bot", new_callable=AsyncMock) as mock_fwd, \
             patch("app.services.messages._touch_conversation"):
            _run(msg_service.process_message("hola", "u1", "c1"))
        mock_fwd.assert_not_called()


class TestHandleWebhook:

    def _payload(self):
        from app.models.xmpp import BotWebhookPayload
        return BotWebhookPayload(from_jid="u@x", body="hola", response="hi", message_id="m1")

    def test_updates_existing_message_when_same_house(self):
        with patch("app.services.messages.message_repository") as mock_m, \
             patch("app.services.messages.conversation_repository") as mock_c, \
             patch("app.services.messages.house_member_repository") as mock_h, \
             patch("app.services.messages.supabase"):
            mock_m.find_by_id.return_value = {"id": "m1", "conversation_id": "c1"}
            mock_c.find_user_id_by_id.return_value = "u1"
            mock_h.find_house_id_by_user.return_value = "h1"
            msg_service.handle_webhook(self._payload(), "h1")

    def test_message_from_other_house_raises_403(self):
        with patch("app.services.messages.message_repository") as mock_m, \
             patch("app.services.messages.conversation_repository") as mock_c, \
             patch("app.services.messages.house_member_repository") as mock_h:
            mock_m.find_by_id.return_value = {"id": "m1", "conversation_id": "c1"}
            mock_c.find_user_id_by_id.return_value = "u1"
            mock_h.find_house_id_by_user.return_value = "h_otra"
            with pytest.raises(HTTPException) as exc:
                msg_service.handle_webhook(self._payload(), "h1")
            assert exc.value.status_code == 403


# ── CRUD ───────────────────────────────────────────────────────────────────

class TestCRUD:

    def test_get_user_messages_returns_list_for_user_conversations(self):
        with patch("app.services.messages.conversation_repository") as mock_c, \
             patch("app.services.messages.message_repository") as mock_m:
            mock_c.find_ids_by_user.return_value = ["c1"]
            mock_m.find_by_conversation_ids.return_value = [{"id": "m1"}]
            assert msg_service.get_user_messages("u1") == [{"id": "m1"}]
