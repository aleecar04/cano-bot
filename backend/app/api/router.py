from fastapi import APIRouter
from app.api.routes import bot, commands, conversations, devices, favorites, houses, schedules, users, messages, login, push

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(messages.router)
api_router.include_router(login.router)
api_router.include_router(devices.router)
api_router.include_router(conversations.router)
api_router.include_router(commands.router)
api_router.include_router(houses.router)
api_router.include_router(schedules.router)
api_router.include_router(favorites.router)
api_router.include_router(push.router)
api_router.include_router(bot.router)
api_router.include_router(bot.internal_router)
