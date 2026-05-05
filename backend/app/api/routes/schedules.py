from fastapi import APIRouter, HTTPException
from app.api.deps import CurrentUser
from app.models import ScheduleCreate, SchedulePublic, ScheduleToggle
from app.services import schedules as svc
from app.services.home import get_user_role

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/", response_model=list[SchedulePublic])
def list_schedules(current_user: CurrentUser):
    return svc.get_schedules(current_user["id"])


@router.post("/", response_model=SchedulePublic, status_code=201)
def create_schedule(schedule_in: ScheduleCreate, current_user: CurrentUser):
    try:
        return svc.create_schedule(schedule_in, current_user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str, current_user: CurrentUser):
    user_id = current_user["id"]
    deleted = svc.delete_schedule(schedule_id, user_id)
    if not deleted:
        if get_user_role(user_id) == "owner":
            deleted = svc.delete_schedule_any(schedule_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")


@router.patch("/{schedule_id}/toggle", response_model=SchedulePublic)
def toggle_schedule(schedule_id: str, toggle_in: ScheduleToggle, current_user: CurrentUser):
    result = svc.toggle_schedule(schedule_id, current_user["id"], toggle_in)
    if not result:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return result
