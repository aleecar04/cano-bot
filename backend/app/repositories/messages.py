from app.core.db import supabase


class MessageRepository:

    EMBED_COMMAND = "*, command:commands(*)"

    def find_by_id(self, message_id: str) -> dict | None:
        res = supabase.table("messages").select("*").eq("id", message_id).limit(1).execute()
        return res.data[0] if res.data else None

    def find_by_conversation(self, conversation_id: str) -> list[dict]:
        return (
            supabase.table("messages")
            .select(self.EMBED_COMMAND)
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
            .data
            or []
        )

    def find_by_conversation_ids(self, conversation_ids: list[str]) -> list[dict]:
        if not conversation_ids:
            return []
        return (
            supabase.table("messages")
            .select(self.EMBED_COMMAND)
            .in_("conversation_id", conversation_ids)
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )


class ConversationRepository:

    def find_by_id_and_user(self, conversation_id: str, user_id: str) -> dict | None:
        res = (
            supabase.table("conversations")
            .select("id")
            .eq("id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_by_user(self, user_id: str) -> list[dict]:
        return (
            supabase.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
            .data
            or []
        )

    def find_ids_by_user(self, user_id: str) -> list[str]:
        res = supabase.table("conversations").select("id").eq("user_id", user_id).execute()
        return [c["id"] for c in (res.data or [])]

    def find_by_user_and_title(self, user_id: str, title: str) -> dict | None:
        res = (
            supabase.table("conversations")
            .select("id")
            .eq("user_id", user_id)
            .eq("title", title)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_user_id_by_id(self, conversation_id: str) -> str | None:
        res = (
            supabase.table("conversations")
            .select("user_id")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
        return res.data[0]["user_id"] if res.data else None


message_repository = MessageRepository()
conversation_repository = ConversationRepository()
