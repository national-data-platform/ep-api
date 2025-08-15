# api/routes/redirect_routes/__init__.py
from fastapi import APIRouter

from .service_redirect import router as service_redirect_router

router = APIRouter()

router.include_router(service_redirect_router)
