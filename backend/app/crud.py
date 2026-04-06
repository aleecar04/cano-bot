from app.core.db import supabase
from app.models import UserUpdate


def get_user_by_email(email: str) -> dict | None:
    result = supabase.table("base_user").select("*").eq("email", email).execute()
    return result.data[0] if result.data else None


def update_user(user_id, user_in: UserUpdate) -> dict:
    data = user_in.model_dump(exclude_unset=True)
    data.pop("password", None)
    result = supabase.table("base_user").update(data).eq("id", str(user_id)).execute()
    return result.data[0]