from app.core.db import supabase


class HAIntegrationRepository:

    def find_credentials_by_house(self, house_id: str) -> dict | None:
        res = (
            supabase.table("ha_integrations")
            .select("ha_url, token")
            .eq("house_id", house_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def find_summary_by_house(self, house_id: str) -> dict | None:
        res = (
            supabase.table("ha_integrations")
            .select("ha_url, created_at")
            .eq("house_id", house_id)
            .execute()
        )
        return res.data[0] if res.data else None

ha_integration_repository = HAIntegrationRepository()
