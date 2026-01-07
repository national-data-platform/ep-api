# api/routes/status_routes/__init__.py

from fastapi import APIRouter

from ...config.swagger_settings import swagger_settings
from ...config.rexec_settings import rexec_settings
from .get import router as get_router
from .get_jupyter import router as get_jupyter_router
from .kafka_details import router as kafka_router
from .get_rexec_api import router as get_rexec_router

router = APIRouter()

router.include_router(get_router)
router.include_router(kafka_router)
if swagger_settings.use_jupyterlab:
    router.include_router(get_jupyter_router)
if rexec_settings.connection:
    router.include_router(get_rexec_router)
