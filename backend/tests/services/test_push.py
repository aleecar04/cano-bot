from unittest.mock import MagicMock, patch

from pywebpush import WebPushException

from app.services import push as push_service


class TestPushService:

    def test_sends_to_each_subscription(self):
        subs = [{"id": f"sub_{i}", "endpoint": f"e{i}", "p256dh": "k", "auth": "a"} for i in (1, 2)]
        with patch("app.services.push.settings") as mock_s, \
             patch("app.services.push.push_subscription_repository") as mock_repo, \
             patch("app.services.push.webpush") as mock_wp:
            mock_s.VAPID_PRIVATE_KEY = "priv"
            mock_s.VAPID_CONTACT_EMAIL = "ops@cano-app.com"
            mock_repo.find_by_user.return_value = subs
            push_service.send_push("user_anabel", "title", "body")
        assert mock_wp.call_count == 2

    def test_410_drops_subscription_others_swallowed(self):
        sub = {"id": "sub_1", "endpoint": "e1", "p256dh": "k1", "auth": "a1"}
        resp = MagicMock(); resp.status_code = 410
        with patch("app.services.push.settings") as mock_s, \
             patch("app.services.push.push_subscription_repository") as mock_repo, \
             patch("app.services.push.webpush", side_effect=WebPushException("gone", response=resp)), \
             patch("app.services.push.supabase") as mock_db:
            mock_s.VAPID_PRIVATE_KEY = "priv"
            mock_s.VAPID_CONTACT_EMAIL = "ops@cano-app.com"
            mock_repo.find_by_user.return_value = [sub]
            push_service.send_push("user_anabel", "t", "b")
        mock_db.table.assert_called()

        with patch("app.services.push.settings") as mock_s, \
             patch("app.services.push.push_subscription_repository") as mock_repo, \
             patch("app.services.push.webpush", side_effect=RuntimeError("net")):
            mock_s.VAPID_PRIVATE_KEY = "priv"
            mock_s.VAPID_CONTACT_EMAIL = "ops@cano-app.com"
            mock_repo.find_by_user.return_value = [sub]
            push_service.send_push("user_anabel", "t", "b")

    def test_subscribe_upserts_with_endpoint_as_conflict_key(self):
        with patch("app.services.push.supabase") as mock_db:
            push_service.subscribe("user_anabel", "ep", "p256", "auth")
        mock_db.table.assert_called_with("push_subscriptions")
        assert mock_db.table.return_value.upsert.call_args.kwargs["on_conflict"] == "endpoint"
