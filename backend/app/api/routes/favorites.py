from fastapi import APIRouter
from app.api.deps import CurrentUser
from app.core.errors import not_found
from app.models.favorites import FavoriteActionCreate, FavoriteActionUpdate, FavoriteActionPublic
from app.services import favorites as svc

router = APIRouter(prefix="/favorite-actions", tags=["favorites"])


@router.get("/", response_model=list[FavoriteActionPublic])
def list_favorites(current_user: CurrentUser):
    return svc.get_favorites(current_user["id"])


@router.post(
    "/",
    response_model=FavoriteActionPublic,
    status_code=201,
    responses={400: {"description": "Device limit reached or duplicate"}},
)
def add_favorite(fav_in: FavoriteActionCreate, current_user: CurrentUser):
    return svc.add_favorite(fav_in, current_user["id"])


@router.post("/{favorite_id}/execute")
async def execute_favorite(favorite_id: str, current_user: CurrentUser):
    return await svc.execute_favorite(favorite_id, current_user["id"])


@router.patch("/{favorite_id}", response_model=FavoriteActionPublic)
def update_favorite(favorite_id: str, fav_in: FavoriteActionUpdate, current_user: CurrentUser):
    updated = svc.update_favorite(favorite_id, current_user["id"], fav_in.action, fav_in.payload, fav_in.label)
    if not updated:
        raise not_found("Favorito no encontrado")
    return updated


@router.delete("/{favorite_id}", status_code=204)
def delete_favorite(favorite_id: str, current_user: CurrentUser):
    deleted = svc.delete_favorite(favorite_id, current_user["id"])
    if not deleted:
        raise not_found("Favorito no encontrado")
