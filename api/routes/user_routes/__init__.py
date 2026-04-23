# api/routes/user_routes/__init__.py

from fastapi import APIRouter

from .access_requests import router as access_requests_router
from .user_info import router as user_info_router
from .user_login import router as user_login_router

router = APIRouter()

router.include_router(user_info_router)
router.include_router(user_login_router)
router.include_router(access_requests_router)
