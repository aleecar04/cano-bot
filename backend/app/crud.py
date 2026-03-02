import uuid
from app.core.db import supabase
from app.models import ItemCreate, UserCreate, UserUpdate

def create_user(*, user_create: UserCreate) -> dict:
    response = supabase.auth.admin.create_user({
        "email": user_create.email,
        "password": user_create.password,
        "user_metadata": {
            "full_name": user_create.full_name,
            "is_superuser": user_create.is_superuser,
        },
        "email_confirm": True,
    })
    user = response.user
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user_create.full_name,
        "is_active": True,
        "is_superuser": user_create.is_superuser,
        "created_at": str(user.created_at),
    }

def get_user_by_email(*, email: str) -> dict | None:
    response = supabase.auth.admin.list_users()
    for user in response:
        if user.email == email:
            return {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.user_metadata.get("full_name"),
                "is_active": True,
                "is_superuser": user.user_metadata.get("is_superuser", False),
                "created_at": str(user.created_at),
            }
    return None

def update_user(*, user_id: uuid.UUID, user_in: UserUpdate) -> dict:
    data = {}
    if user_in.email:
        data["email"] = user_in.email
    if user_in.password:
        data["password"] = user_in.password
    if user_in.full_name is not None:
        data.setdefault("user_metadata", {})["full_name"] = user_in.full_name
    response = supabase.auth.admin.update_user_by_id(str(user_id), data)
    user = response.user
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.user_metadata.get("full_name"),
        "is_active": True,
        "is_superuser": user.user_metadata.get("is_superuser", False),
        "created_at": str(user.created_at),
    }

def authenticate(*, email: str, password: str) -> dict | None:
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        user = response.user
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.user_metadata.get("full_name"),
            "is_active": True,
            "is_superuser": user.user_metadata.get("is_superuser", False),
            "created_at": str(user.created_at),
        }
    except Exception:
        return None

def create_item(*, item_in: ItemCreate, owner_id: uuid.UUID) -> dict:
    data = item_in.model_dump()
    data["owner_id"] = str(owner_id)
    result = supabase.table("item").insert(data).execute()
    return result.data[0]