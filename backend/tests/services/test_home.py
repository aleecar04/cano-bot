from unittest.mock import MagicMock, patch
from fastapi import HTTPException
import pytest

from app.services import home as home_service


# ── _generate_bot_token / _hash_bot_token ──────────────────────────────────

class TestBotToken:

    def test_genera_token_no_vacio(self):
        from app.services.home import _generate_bot_token
        token = _generate_bot_token()
        assert isinstance(token, str)
        assert len(token) > 20

    def test_hash_es_sha256_hex(self):
        from app.services.home import _hash_bot_token
        h = _hash_bot_token("abc")
        assert len(h) == 64  # sha256 hex
        assert all(c in "0123456789abcdef" for c in h)

    def test_dos_tokens_distintos(self):
        from app.services.home import _generate_bot_token
        assert _generate_bot_token() != _generate_bot_token()


class TestBotResourceFromTokenHash:

    def test_devuelve_prefijo_bot_y_12_chars(self):
        from app.services.home import _bot_resource_from_token_hash
        h = "abcdef1234567890fedcba9876543210"
        assert _bot_resource_from_token_hash(h) == "bot-abcdef123456"


class TestGenerateInvitationCode:

    def test_genera_codigo_de_6_caracteres(self):
        with patch("app.services.home.house_invitation_repository"), \
             patch("app.services.home.supabase"):
            code = home_service.generate_invitation_code("h1", "u1")
        assert len(code) == 6
        assert all(c.isalnum() and c.upper() == c for c in code)


# ── consume_invitation_code ────────────────────────────────────────────────

class TestConsumeInvitationCode:

    def test_codigo_invalido_lanza_400(self):
        with patch("app.services.home.house_invitation_repository") as mock_inv:
            mock_inv.find_unused_by_code.return_value = None
            with pytest.raises(HTTPException) as exc:
                home_service.consume_invitation_code("BAD123", "u1")
            assert exc.value.status_code == 400

    def test_codigo_caducado_lanza_400(self):
        from datetime import datetime, timezone, timedelta
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        with patch("app.services.home.house_invitation_repository") as mock_inv:
            mock_inv.find_unused_by_code.return_value = {
                "house_id": "h1", "expires_at": past,
            }
            with pytest.raises(HTTPException) as exc:
                home_service.consume_invitation_code("OLD", "u1")
            assert exc.value.status_code == 400

    def test_codigo_valido_inserta_member_y_marca_used(self):
        from datetime import datetime, timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        with patch("app.services.home.house_invitation_repository") as mock_inv, \
             patch("app.services.home.house_repository") as mock_h, \
             patch("app.services.home.supabase") as mock_db:
            mock_inv.find_unused_by_code.return_value = {
                "id": "i1", "code": "GOOD", "house_id": "h1", "expires_at": future,
            }
            mock_h.find_by_id.return_value = {"id": "h1", "name": "Casa"}
            result = home_service.consume_invitation_code("GOOD", "u1")
        assert result["id"] == "h1"


# ── Helpers ────────────────────────────────────────────────────────────────

class TestGetUserHouse:

    def test_sin_house_id_devuelve_none(self):
        with patch("app.services.home.house_member_repository") as mock_h:
            mock_h.find_house_id_by_user.return_value = None
            assert home_service.get_user_house("u1") is None

    def test_con_house_id_devuelve_house(self):
        with patch("app.services.home.house_member_repository") as mock_hm, \
             patch("app.services.home.house_repository") as mock_h:
            mock_hm.find_house_id_by_user.return_value = "h1"
            mock_h.find_by_id.return_value = {"id": "h1"}
            assert home_service.get_user_house("u1") == {"id": "h1"}


class TestGetBotTargetForUser:

    def test_sin_house_devuelve_none(self):
        with patch("app.services.home.house_member_repository") as mock_h:
            mock_h.find_house_id_by_user.return_value = None
            assert home_service.get_bot_target_for_user("u1") is None

    def test_house_sin_token_devuelve_none(self):
        with patch("app.services.home.house_member_repository") as mock_hm, \
             patch("app.services.home.house_repository") as mock_h:
            mock_hm.find_house_id_by_user.return_value = "h1"
            mock_h.find_by_id.return_value = {"id": "h1"}  # sin bot_token_hash
            assert home_service.get_bot_target_for_user("u1") is None

    def test_devuelve_jid_con_resource(self):
        with patch("app.services.home.house_member_repository") as mock_hm, \
             patch("app.services.home.house_repository") as mock_h, \
             patch("app.core.config.settings") as mock_s:
            mock_hm.find_house_id_by_user.return_value = "h1"
            mock_h.find_by_id.return_value = {"id": "h1", "bot_token_hash": "abcdef1234567890"}
            mock_s.XMPP_BOT_JID = "bot@xmpp"
            result = home_service.get_bot_target_for_user("u1")
        assert "bot@xmpp" in result
        assert "bot-abcdef123456" in result


class TestRequireHouse:

    def test_sin_house_lanza_403(self):
        with patch("app.services.home.house_member_repository") as mock_h:
            mock_h.find_house_id_by_user.return_value = None
            with pytest.raises(HTTPException) as exc:
                home_service.require_house("u1")
            assert exc.value.status_code == 403

    def test_con_house_devuelve_id(self):
        with patch("app.services.home.house_member_repository") as mock_h:
            mock_h.find_house_id_by_user.return_value = "h1"
            assert home_service.require_house("u1") == "h1"


class TestRequireOwner:

    def test_no_owner_lanza_403(self):
        with patch("app.services.home.get_user_role", return_value="member"):
            with pytest.raises(HTTPException) as exc:
                home_service.require_owner("u1")
            assert exc.value.status_code == 403

    def test_owner_pasa_sin_lanzar(self):
        with patch("app.services.home.get_user_role", return_value="owner"):
            home_service.require_owner("u1")  # no lanza


class TestGetHouseMemberIds:

    def test_sin_house_devuelve_solo_user(self):
        with patch("app.services.home.house_member_repository") as mock_h:
            mock_h.find_house_id_by_user.return_value = None
            assert home_service.get_house_member_ids("u1") == ["u1"]

    def test_con_house_devuelve_lista(self):
        with patch("app.services.home.house_member_repository") as mock_h:
            mock_h.find_house_id_by_user.return_value = "h1"
            mock_h.find_user_ids_by_house.return_value = ["u1", "u2"]
            assert home_service.get_house_member_ids("u1") == ["u1", "u2"]


# ── setup_house con rollback ───────────────────────────────────────────────

class TestSetupHouse:

    def test_usuario_ya_en_casa_lanza_409(self):
        with patch("app.services.home.get_house_id_for_user", return_value="h_existente"):
            with pytest.raises(HTTPException) as exc:
                home_service.setup_house("u1", "Mi Casa")
            assert exc.value.status_code == 409

    def test_flujo_completo_devuelve_token(self):
        with patch("app.services.home.get_house_id_for_user", return_value=None), \
             patch("app.services.home.supabase") as mock_db:
            # houses.insert devuelve house creada
            mock_houses_chain = MagicMock()
            mock_houses_chain.execute.return_value.data = [{"id": "h_new"}]
            # mock distinto por tabla
            def table_side(name):
                m = MagicMock()
                if name == "houses":
                    m.insert.return_value = mock_houses_chain
                else:
                    m.insert.return_value.execute.return_value = MagicMock()
                m.delete.return_value.eq.return_value.execute.return_value = MagicMock()
                return m
            mock_db.table.side_effect = table_side
            result = home_service.setup_house("u1", "X")
        assert result["house_id"] == "h_new"
        assert isinstance(result["bot_token"], str)

    def test_house_members_falla_borra_house(self):
        with patch("app.services.home.get_house_id_for_user", return_value=None), \
             patch("app.services.home.supabase") as mock_db:
            mock_houses_chain = MagicMock()
            mock_houses_chain.execute.return_value.data = [{"id": "h_new"}]
            mock_delete_chain = MagicMock()
            def table_side(name):
                m = MagicMock()
                if name == "houses":
                    m.insert.return_value = mock_houses_chain
                    m.delete.return_value.eq.return_value.execute.return_value = mock_delete_chain
                else:
                    m.insert.return_value.execute.side_effect = RuntimeError("members fail")
                return m
            mock_db.table.side_effect = table_side
            with pytest.raises(RuntimeError):
                home_service.setup_house("u1", "X")
            # Verificar que se intentó borrar la house
            calls = [c.args[0] for c in mock_db.table.call_args_list]
            assert calls.count("houses") >= 2


class TestRegenerateBotToken:

    def test_devuelve_token_nuevo(self):
        with patch("app.services.home.require_owner"), \
             patch("app.services.home.require_house", return_value="h1"), \
             patch("app.services.home.supabase") as mock_db:
            token = home_service.regenerate_bot_token("u1")
        assert isinstance(token, str)
        assert len(token) > 20
