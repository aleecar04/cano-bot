from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser
from app.models import FavoriteActionCreate, FavoriteActionPublic
from app.services import favorites as svc

router = APIRouter(prefix="/favorite-actions", tags=["favorites"])


@router.get("/", response_model=list[FavoriteActionPublic])
def list_favorites(current_user: CurrentUser):
    return svc.get_favorites(current_user["id"])


@router.post("/", response_model=FavoriteActionPublic, status_code=201)
def add_favorite(fav_in: FavoriteActionCreate, current_user: CurrentUser):
    try:
        return svc.add_favorite(fav_in, current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{favorite_id}/execute")
async def execute_favorite(favorite_id: str, current_user: CurrentUser):
    try:
        return await svc.execute_favorite(favorite_id, current_user["id"])
    except ValueError as e:
        msg = str(e)
        status = 404 if "no encontrado" in msg.lower() else 400
        raise HTTPException(status_code=status, detail=msg)


@router.delete("/{favorite_id}", status_code=204)
def delete_favorite(favorite_id: str, current_user: CurrentUser):
    deleted = svc.delete_favorite(favorite_id, current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Favorito no encontrado")
