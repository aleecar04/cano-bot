from fastapi import APIRouter
from app.api.routes import admin, commands, conversations, devices, favorites, houses, schedules, users, utils, messages, login

api_router = APIRouter()
api_router.include_router(admin.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(messages.router)
api_router.include_router(login.router)
api_router.include_router(devices.router)
api_router.include_router(conversations.router)
api_router.include_router(commands.router)
api_router.include_router(houses.router)
api_router.include_router(schedules.router)
api_router.include_router(favorites.router)
