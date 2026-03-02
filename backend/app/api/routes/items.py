import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.core.db import supabase
from app.models import ItemCreate, ItemPublic, ItemsPublic, ItemUpdate, Message

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=ItemsPublic)
def read_items(current_user: CurrentUser, skip: int = 0, limit: int = 100) -> Any:
    if current_user.get("is_superuser"):
        result = supabase.table("item").select("*", count="exact").range(skip, skip + limit - 1).order("created_at", desc=True).execute()
    else:
        result = supabase.table("item").select("*", count="exact").eq("owner_id", current_user["id"]).range(skip, skip + limit - 1).order("created_at", desc=True).execute()
    return ItemsPublic(data=result.data, count=result.count)


@router.get("/{id}", response_model=ItemPublic)
def read_item(current_user: CurrentUser, id: uuid.UUID) -> Any:
    result = supabase.table("item").select("*").eq("id", str(id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Item not found")
    item = result.data[0]
    if not current_user.get("is_superuser") and item["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return item


@router.post("/", response_model=ItemPublic)
def create_item(*, current_user: CurrentUser, item_in: ItemCreate) -> Any:
    data = item_in.model_dump()
    data["owner_id"] = current_user["id"]
    result = supabase.table("item").insert(data).execute()
    return result.data[0]


@router.put("/{id}", response_model=ItemPublic)
def update_item(*, current_user: CurrentUser, id: uuid.UUID, item_in: ItemUpdate) -> Any:
    result = supabase.table("item").select("*").eq("id", str(id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Item not found")
    item = result.data[0]
    if not current_user.get("is_superuser") and item["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    update_data = item_in.model_dump(exclude_unset=True)
    result = supabase.table("item").update(update_data).eq("id", str(id)).execute()
    return result.data[0]


@router.delete("/{id}")
def delete_item(current_user: CurrentUser, id: uuid.UUID) -> Message:
    result = supabase.table("item").select("*").eq("id", str(id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Item not found")
    item = result.data[0]
    if not current_user.get("is_superuser") and item["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    supabase.table("item").delete().eq("id", str(id)).execute()
    return Message(message="Item deleted successfully")