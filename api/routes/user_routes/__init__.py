# api/routes/user_routes/__init__.py

from fastapi import APIRouter

from .user_info import router as user_info_router

router = APIRouter()

router.include_router(user_info_router)
