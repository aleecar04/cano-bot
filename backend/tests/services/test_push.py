from unittest.mock import MagicMock, patch

from pywebpush import WebPushException

from app.services import push as push_service


class TestSendPush:

    def test_no_vapid_key_skips_lookup(self):
        with patch("app.services.push.settings") as mock_s, \
             patch("app.services.push.push_subscription_repository") as mock_repo:
            mock_s.VAPID_PRIVATE_KEY = ""
            push_service.send_push("u1", "title", "body")
        mock_repo.find_by_user.assert_not_called()

    def test_sends_to_each_subscription(self):
        subs = [{"id": f"s{i}", "endpoint": f"e{i}", "p256dh": "k", "auth": "a"} for i in (1, 2)]
        with patch("app.services.push.settings") as mock_s, \
             patch("app.services.push.push_subscription_repository") as mock_repo, \
             patch("app.services.push.webpush") as mock_wp:
            mock_s.VAPID_PRIVATE_KEY = "priv"
            mock_s.VAPID_CONTACT_EMAIL = "x@y.com"
            mock_repo.find_by_user.return_value = subs
            push_service.send_push("u1", "title", "body")
        assert mock_wp.call_count == 2

    def test_410_deletes_subscription_and_other_errors_are_silenced(self):
        sub = {"id": "s1", "endpoint": "e1", "p256dh": "k1", "auth": "a1"}
        resp = MagicMock(); resp.status_code = 410
        with patch("app.services.push.settings") as mock_s, \
             patch("app.services.push.push_subscription_repository") as mock_repo, \
             patch("app.services.push.webpush", side_effect=WebPushException("gone", response=resp)), \
             patch("app.services.push.supabase") as mock_db:
            mock_s.VAPID_PRIVATE_KEY = "priv"
            mock_s.VAPID_CONTACT_EMAIL = "x@y.com"
            mock_repo.find_by_user.return_value = [sub]
            push_service.send_push("u1", "t", "b")
        mock_db.table.assert_called()

        with patch("app.services.push.settings") as mock_s, \
             patch("app.services.push.push_subscription_repository") as mock_repo, \
             patch("app.services.push.webpush", side_effect=RuntimeError("net")):
            mock_s.VAPID_PRIVATE_KEY = "priv"
            mock_s.VAPID_CONTACT_EMAIL = "x@y.com"
            mock_repo.find_by_user.return_value = [sub]
            push_service.send_push("u1", "t", "b")


def test_subscribe_upserts_with_endpoint_as_conflict_key():
    with patch("app.services.push.supabase") as mock_db:
        push_service.subscribe("u1", "ep", "p256", "auth")
    mock_db.table.assert_called_with("push_subscriptions")
    assert mock_db.table.return_value.upsert.call_args.kwargs["on_conflict"] == "endpoint"


