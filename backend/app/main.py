import asyncio
import logging
import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


async def _schedule_loop() -> None:
    """Background task: runs pending schedules every 60 seconds."""
    while True:
        await asyncio.sleep(60)
        try:
            from app.services.schedules import get_pending_schedules
            from app.services.command_executor import execute_command, ScheduleSource
            pending = get_pending_schedules()
            for schedule in pending:
                try:
                    await execute_command(
                        device_id=schedule["device_id"],
                        action=schedule["action"],
                        payload=schedule.get("payload") or {},
                        user_id=schedule["user_id"],
                        source=ScheduleSource(schedule["id"]),
                    )
                except Exception as e:
                    logger.error("Scheduler: schedule %s failed: %s", schedule["id"], e)
        except Exception as e:
            logger.error("Scheduler loop error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_schedule_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
