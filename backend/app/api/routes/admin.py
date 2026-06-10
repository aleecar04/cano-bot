from typing import Any
from fastapi import APIRouter, Depends
from app.api.deps import get_current_active_superuser
from app.services import admin as admin_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.get("/stats")
def get_stats() -> Any:
    return admin_service.get_stats()


@router.get("/houses")
def get_all_houses() -> Any:
    return admin_service.list_houses()


@router.delete("/houses/{house_id}", status_code=204)
def delete_house(house_id: str) -> None:
    admin_service.delete_house(house_id)
