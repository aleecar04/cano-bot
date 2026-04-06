from fastapi import APIRouter
from app.api.routes import users, utils, messages, login
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(messages.router)
api_router.include_router(login.router)