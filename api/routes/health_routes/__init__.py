# api/routes/health_routes/__init__.py

from fastapi import APIRouter

from .health import router as health_router
from .ready import router as ready_router

router = APIRouter()

router.include_router(health_router)
router.include_router(ready_router)
