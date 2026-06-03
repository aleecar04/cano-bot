from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
import asyncio
import pytest

from app.services import messages as msg_service


def _run(coro):
    return asyncio.run(coro)


# ── _require_bot_target ──────────────────────────────────────────────────────

class TestRequireBotTarget:

    def test_sin_target_lanza_400(self):
        with patch("app.services.messages.get_bot_target_for_user", return_value=None):
            with pytest.raises(HTTPException) as exc:
                msg_service._require_bot_target("u1")
            assert exc.value.status_code == 400

    def test_con_target_devuelve_jid(self):
        with patch("app.services.messages.get_bot_target_for_user", return_value="bot@x"):
            assert msg_service._require_bot_target("u1") == "bot@x"


# ── _authenticate_gajim_sender ──────────────────────────────────────────────

class TestAuthenticateGajimSender:

    def test_jid_desconocido_lanza_404(self):
        with patch("app.services.messages.xmpp_account_repository") as mock_x:
            mock_x.find_user_id_by_jid.return_value = None
            with pytest.raises(HTTPException) as exc:
                msg_service._authenticate_gajim_sender("ghost@x", "h1")
            assert exc.value.status_code == 404

    def test_jid_de_otra_casa_lanza_404(self):
        with patch("app.services.messages.xmpp_account_repository") as mock_x, \
             patch("app.services.messages.house_member_repository") as mock_h:
            mock_x.find_user_id_by_jid.return_value = "u1"
            mock_h.find_house_id_by_user.return_value = "h_otra"
            with pytest.raises(HTTPException) as exc:
                msg_service._authenticate_gajim_sender("u@x", "h1")
            assert exc.value.status_code == 404

    def test_devuelve_user_id_si_member(self):
        with patch("app.services.messages.xmpp_account_repository") as mock_x, \
             patch("app.services.messages.house_member_repository") as mock_h:
            mock_x.find_user_id_by_jid.return_value = "u1"
            mock_h.find_house_id_by_user.return_value = "h1"
            assert msg_service._authenticate_gajim_sender("u@x/res", "h1") == "u1"


# ── _classify ───────────────────────────────────────────────────────────────

class TestClassify:

    def test_comando_conocido_no_llama_ollama(self):
        with patch("app.services.messages.classify_intent", new_callable=AsyncMock) as mock_o:
            result = _run(msg_service._classify("!ayuda"))
        assert result == {"intent": "ayuda"}
        mock_o.assert_not_awaited()

    def test_comando_desconocido_devuelve_none(self):
        with patch("app.services.messages.classify_intent", new_callable=AsyncMock) as mock_o:
            result = _run(msg_service._classify("!inventado"))
        assert result is None
        mock_o.assert_not_awaited()

    def test_texto_natural_llama_ollama(self):
        with patch("app.services.messages.classify_intent",
                   new_callable=AsyncMock, return_value={"intent": "control_device"}) as mock_o:
            result = _run(msg_service._classify("enciende la luz"))
        assert result == {"intent": "control_device"}
        mock_o.assert_awaited_once()


# ── _device_not_found_message ───────────────────────────────────────────────

class TestDeviceNotFoundMessage:

    def test_con_nombre_lo_incluye(self):
        msg = msg_service._device_not_found_message({"dispositivo": "luz salón"})
        assert "luz salón" in msg

    def test_sin_nombre_mensaje_generico(self):
        msg = msg_service._device_not_found_message({})
        assert "qué dispositivo" in msg


# ── _try_resolve_in_backend ─────────────────────────────────────────────────

class TestTryResolveInBackend:

    def test_intent_none_resuelve_unknown(self):
        async def fake_resolve(mid, text):
            fake_resolve.calls.append((mid, text))
        fake_resolve.calls = []
        result = _run(msg_service._try_resolve_in_backend(
            None, "u1", {"id": "m1"}, fake_resolve,
        ))
        assert result is True
        assert fake_resolve.calls[0][0] == "m1"

    def test_backend_resolved_intent(self):
        async def fake_resolve(mid, text):
            fake_resolve.calls.append((mid, text))
        fake_resolve.calls = []
        result = _run(msg_service._try_resolve_in_backend(
            {"intent": "unknown"}, "u1", {"id": "m1"}, fake_resolve,
        ))
        assert result is True
        assert "entendido" in fake_resolve.calls[0][1].lower()

    def test_intent_no_resoluble_devuelve_false(self):
        async def fake_resolve(mid, text):
            fake_resolve.calls.append((mid, text))
        fake_resolve.calls = []
        result = _run(msg_service._try_resolve_in_backend(
            {"intent": "ayuda"}, "u1", {"id": "m1"}, fake_resolve,
        ))
        assert result is False
        assert fake_resolve.calls == []

    def test_control_device_validation_error(self):
        async def fake_resolve(mid, text):
            fake_resolve.calls.append((mid, text))
        fake_resolve.calls = []
        with patch("app.services.messages._dispatch_device_from_nlp",
                   new_callable=AsyncMock, side_effect=msg_service._ValidationError("acción inválida")):
            result = _run(msg_service._try_resolve_in_backend(
                {"intent": "control_device"}, "u1", {"id": "m1"}, fake_resolve,
            ))
        assert result is True
        assert fake_resolve.calls[0][1] == "acción inválida"

    def test_control_device_device_not_found(self):
        async def fake_resolve(mid, text):
            fake_resolve.calls.append((mid, text))
        fake_resolve.calls = []
        with patch("app.services.messages._dispatch_device_from_nlp",
                   new_callable=AsyncMock, side_effect=msg_service._DeviceNotFound()):
            result = _run(msg_service._try_resolve_in_backend(
                {"intent": "control_device", "dispositivo": "fantasma"},
                "u1", {"id": "m1"}, fake_resolve,
            ))
        assert result is True
        assert "fantasma" in fake_resolve.calls[0][1]

    def test_control_device_exito_no_llama_resolve(self):
        async def fake_resolve(mid, text):
            fake_resolve.calls.append((mid, text))
        fake_resolve.calls = []
        with patch("app.services.messages._dispatch_device_from_nlp", new_callable=AsyncMock):
            result = _run(msg_service._try_resolve_in_backend(
                {"intent": "control_device"}, "u1", {"id": "m1"}, fake_resolve,
            ))
        assert result is True
        assert fake_resolve.calls == []


# ── _dispatch_device_from_nlp ───────────────────────────────────────────────

class TestDispatchDeviceFromNlp:

    def test_sin_action_lanza_device_not_found(self):
        with pytest.raises(msg_service._DeviceNotFound):
            _run(msg_service._dispatch_device_from_nlp({}, "u1", "m1"))

    def test_sin_house_lanza_device_not_found(self):
        with patch("app.services.messages.get_house_id_for_user", return_value=None):
            with pytest.raises(msg_service._DeviceNotFound):
                _run(msg_service._dispatch_device_from_nlp(
                    {"accion": "encender", "dispositivo": "luz"}, "u1", "m1",
                ))

    def test_device_no_existe_lanza_device_not_found(self):
        with patch("app.services.messages.get_house_id_for_user", return_value="h1"), \
             patch("app.services.messages.device_repository") as mock_d:
            mock_d.find_by_name_and_house.return_value = None
            with pytest.raises(msg_service._DeviceNotFound):
                _run(msg_service._dispatch_device_from_nlp(
                    {"accion": "encender", "dispositivo": "fantasma"}, "u1", "m1",
                ))

    def test_accion_no_soportada_lanza_validation_error(self):
        with patch("app.services.messages.get_house_id_for_user", return_value="h1"), \
             patch("app.services.messages.device_repository") as mock_d:
            mock_d.find_by_name_and_house.return_value = {
                "id": "d1", "name": "Enchufe", "type": "Enchufe",
            }
            with pytest.raises(msg_service._ValidationError):
                _run(msg_service._dispatch_device_from_nlp(
                    {"accion": "brillo", "dispositivo": "enchufe", "payload": {"valor": 50}},
                    "u1", "m1",
                ))

    def test_payload_invalido_lanza_validation_error(self):
        with patch("app.services.messages.get_house_id_for_user", return_value="h1"), \
             patch("app.services.messages.device_repository") as mock_d:
            mock_d.find_by_name_and_house.return_value = {
                "id": "d1", "name": "Luz", "type": "Luz",
            }
            with pytest.raises(msg_service._ValidationError):
                _run(msg_service._dispatch_device_from_nlp(
                    {"accion": "brillo", "dispositivo": "luz", "payload": {"valor": 200}},
                    "u1", "m1",
                ))


# ── handle_webhook ──────────────────────────────────────────────────────────

class TestHandleWebhook:

    def test_message_existente_actualiza_response(self):
        from app.models.xmpp import BotWebhookPayload
        payload = BotWebhookPayload(
            from_jid="u@x", body="hola", response="hi", message_id="m1",
        )
        with patch("app.services.messages.message_repository") as mock_m, \
             patch("app.services.messages.conversation_repository") as mock_c, \
             patch("app.services.messages.house_member_repository") as mock_h, \
             patch("app.services.messages.supabase"):
            mock_m.find_by_id.return_value = {"id": "m1", "conversation_id": "c1"}
            mock_c.find_user_id_by_id.return_value = "u1"
            mock_h.find_house_id_by_user.return_value = "h1"
            msg_service.handle_webhook(payload, "h1")

    def test_message_de_otra_casa_lanza_403(self):
        from app.models.xmpp import BotWebhookPayload
        payload = BotWebhookPayload(
            from_jid="u@x", body="hola", response="hi", message_id="m1",
        )
        with patch("app.services.messages.message_repository") as mock_m, \
             patch("app.services.messages.conversation_repository") as mock_c, \
             patch("app.services.messages.house_member_repository") as mock_h:
            mock_m.find_by_id.return_value = {"id": "m1", "conversation_id": "c1"}
            mock_c.find_user_id_by_id.return_value = "u1"
            mock_h.find_house_id_by_user.return_value = "h_otra"
            with pytest.raises(HTTPException) as exc:
                msg_service.handle_webhook(payload, "h1")
            assert exc.value.status_code == 403


# ── CRUD ───────────────────────────────────────────────────────────────────

class TestCRUD:

    def test_get_user_messages_devuelve_lista(self):
        with patch("app.services.messages.conversation_repository") as mock_c, \
             patch("app.services.messages.message_repository") as mock_m:
            mock_c.find_ids_by_user.return_value = ["c1"]
            mock_m.find_by_conversation_ids.return_value = [{"id": "m1"}]
            result = msg_service.get_user_messages("u1")
        assert result == [{"id": "m1"}]

    def test_create_conversation_inserta(self):
        with patch("app.services.messages.supabase") as mock_db:
            mock_db.table.return_value.insert.return_value.execute.return_value.data = [{"id": "c1"}]
            result = msg_service.create_conversation("u1", "Title")
        assert result == {"id": "c1"}

    def test_get_user_conversations(self):
        with patch("app.services.messages.conversation_repository") as mock_c:
            mock_c.find_by_user.return_value = [{"id": "c1"}]
            assert msg_service.get_user_conversations("u1") == [{"id": "c1"}]

    def test_get_conversation_messages(self):
        with patch("app.services.messages.message_repository") as mock_m:
            mock_m.find_by_conversation.return_value = [{"id": "m1"}]
            assert msg_service.get_conversation_messages("c1") == [{"id": "m1"}]
