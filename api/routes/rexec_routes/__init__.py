# api/routes/register_routes/__init__.py

from fastapi import APIRouter
from .post_rexec import router as post_rexec_router

router = APIRouter()

router.include_router(post_rexec_router)
