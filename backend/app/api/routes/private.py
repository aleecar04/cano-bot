from typing import Any
from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.models import UserPublic, PrivateUserCreate
from app.services.users import create_user_simple

router = APIRouter(tags=["private"], prefix="/private")

@router.post("/users/", response_model=UserPublic)
async def create_user(user_in: PrivateUserCreate) -> Any:
    if "production" in settings.ENVIRONMENT:
        raise HTTPException(status_code=403, detail="Not available in production")
    return await create_user_simple(email=user_in.email, password=user_in.password)