from fastapi import APIRouter
from app.api.deps import CurrentUser
from app.core.errors import not_found
from app.models.schedules import ScheduleCreate, SchedulePublic, ScheduleToggle
from app.services.schedules import schedules_service
from app.services.home import home_service

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/", response_model=list[SchedulePublic])
def list_schedules(current_user: CurrentUser):
    return schedules_service.get_schedules(current_user["id"])


@router.post("/", response_model=SchedulePublic, status_code=201)
def create_schedule(schedule_in: ScheduleCreate, current_user: CurrentUser):
    return schedules_service.create_schedule(schedule_in, current_user["id"])


@router.delete("/completed", status_code=200)
def delete_completed_schedules(current_user: CurrentUser):
    count = schedules_service.delete_completed_schedules(current_user["id"])
    return {"deleted": count}


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str, current_user: CurrentUser):
    user_id = current_user["id"]
    deleted = schedules_service.delete_schedule(schedule_id, user_id)
    if not deleted and home_service.get_user_role(user_id) == "owner":
        schedules_service.delete_schedule_any(schedule_id, user_id)


@router.patch("/{schedule_id}/toggle", response_model=SchedulePublic)
def toggle_schedule(schedule_id: str, toggle_in: ScheduleToggle, current_user: CurrentUser):
    user_id = current_user["id"]
    result = schedules_service.toggle_schedule(schedule_id, user_id, toggle_in)
    if not result:
        if home_service.get_user_role(user_id) == "owner":
            result = schedules_service.toggle_schedule_any(schedule_id, user_id, toggle_in)
        if not result:
            raise not_found("Tarea no encontrada")
    return result
