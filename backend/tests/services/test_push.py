from unittest.mock import MagicMock, patch
from pywebpush import WebPushException

from app.services import push as push_service


class TestSendPush:

    def test_sin_vapid_key_no_hace_nada(self):
        with patch("app.services.push.settings") as mock_s:
            mock_s.VAPID_PRIVATE_KEY = ""
            with patch("app.services.push.push_subscription_repository") as mock_repo:
                push_service.send_push("u1", "title", "body")
            mock_repo.find_by_user.assert_not_called()

    def test_envia_a_cada_subscription(self):
        subs = [
            {"id": "s1", "endpoint": "e1", "p256dh": "k1", "auth": "a1"},
            {"id": "s2", "endpoint": "e2", "p256dh": "k2", "auth": "a2"},
        ]
        with patch("app.services.push.settings") as mock_s, \
             patch("app.services.push.push_subscription_repository") as mock_repo, \
             patch("app.services.push.webpush") as mock_wp:
            mock_s.VAPID_PRIVATE_KEY = "priv"
            mock_s.VAPID_CONTACT_EMAIL = "x@y.com"
            mock_repo.find_by_user.return_value = subs
            push_service.send_push("u1", "title", "body")
        assert mock_wp.call_count == 2

    def test_webpush_404_borra_subscription(self):
        sub = {"id": "s1", "endpoint": "e1", "p256dh": "k1", "auth": "a1"}
        mock_resp = MagicMock()
        mock_resp.status_code = 410
        with patch("app.services.push.settings") as mock_s, \
             patch("app.services.push.push_subscription_repository") as mock_repo, \
             patch("app.services.push.webpush", side_effect=WebPushException("gone", response=mock_resp)), \
             patch("app.services.push.supabase") as mock_db:
            mock_s.VAPID_PRIVATE_KEY = "priv"
            mock_s.VAPID_CONTACT_EMAIL = "x@y.com"
            mock_repo.find_by_user.return_value = [sub]
            push_service.send_push("u1", "t", "b")
        mock_db.table.assert_called()

    def test_webpush_otro_error_silencia(self):
        sub = {"id": "s1", "endpoint": "e1", "p256dh": "k1", "auth": "a1"}
        with patch("app.services.push.settings") as mock_s, \
             patch("app.services.push.push_subscription_repository") as mock_repo, \
             patch("app.services.push.webpush", side_effect=RuntimeError("net")):
            mock_s.VAPID_PRIVATE_KEY = "priv"
            mock_s.VAPID_CONTACT_EMAIL = "x@y.com"
            mock_repo.find_by_user.return_value = [sub]
            push_service.send_push("u1", "t", "b")  # no debe lanzar


class TestSubscribe:

    def test_upsert_con_endpoint_como_conflict(self):
        with patch("app.services.push.supabase") as mock_db:
            push_service.subscribe("u1", "ep", "p256", "auth")
        mock_db.table.assert_called_with("push_subscriptions")
        # comprueba el call a upsert
        kwargs = mock_db.table.return_value.upsert.call_args
        assert kwargs.kwargs["on_conflict"] == "endpoint"


class TestUnsubscribe:

    def test_borra_por_user_id_y_endpoint(self):
        with patch("app.services.push.supabase") as mock_db:
            push_service.unsubscribe("u1", "ep")
        mock_db.table.assert_called_with("push_subscriptions")
