from app.core.db import supabase


class PushSubscriptionRepository:

    def find_by_user(self, user_id: str) -> list[dict]:
        return (
            supabase.table("push_subscriptions")
            .select("id, endpoint, p256dh, auth")
            .eq("user_id", user_id)
            .execute()
            .data
            or []
        )


push_subscription_repository = PushSubscriptionRepository()
