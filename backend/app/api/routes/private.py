from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.db import supabase
from app.core.security import get_password_hash
from app.models import UserPublic

router = APIRouter(tags=["private"], prefix="/private")


class PrivateUserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    is_verified: bool = False


@router.post("/users/", response_model=UserPublic)
def create_user(user_in: PrivateUserCreate) -> Any:
    """
    Create a new user (only for local testing).
    """
    data = {
        "email": user_in.email,
        "full_name": user_in.full_name,
        "hashed_password": get_password_hash(user_in.password),
        "is_active": True,
        "is_superuser": False,
    }
    result = supabase.table("user").insert(data).execute()
    return result.data[0]