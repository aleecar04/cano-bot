from fastapi import APIRouter
from app.api.deps import CurrentUser
from app.core.errors import not_found
from app.models.schedules import ScheduleCreate, SchedulePublic, ScheduleToggle
from app.services import schedules as svc
from app.services.home import get_user_role

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/", response_model=list[SchedulePublic])
def list_schedules(current_user: CurrentUser):
    return svc.get_schedules(current_user["id"])


@router.post("/", response_model=SchedulePublic, status_code=201)
def create_schedule(schedule_in: ScheduleCreate, current_user: CurrentUser):
    return svc.create_schedule(schedule_in, current_user["id"])


@router.delete("/completed", status_code=200)
def delete_completed_schedules(current_user: CurrentUser):
    """Delete all one-time completed schedules for the user's house."""
    count = svc.delete_completed_schedules(current_user["id"])
    return {"deleted": count}


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str, current_user: CurrentUser):
    user_id = current_user["id"]
    deleted = svc.delete_schedule(schedule_id, user_id)
    if not deleted:
        if get_user_role(user_id) == "owner":
            deleted = svc.delete_schedule_any(schedule_id, user_id)
        if not deleted:
            raise not_found("Tarea no encontrada")


@router.patch("/{schedule_id}/toggle", response_model=SchedulePublic)
def toggle_schedule(schedule_id: str, toggle_in: ScheduleToggle, current_user: CurrentUser):
    user_id = current_user["id"]
    result = svc.toggle_schedule(schedule_id, user_id, toggle_in)
    if not result:
        if get_user_role(user_id) == "owner":
            result = svc.toggle_schedule_any(schedule_id, user_id, toggle_in)
        if not result:
            raise not_found("Tarea no encontrada")
    return result
