from fastapi import APIRouter

from .delete_dataset import router as delete_dataset_router
from .delete_organization_route import router as delete_organization_router
from .delete_resource_from_dataset import router as delete_resource_router

router = APIRouter()

router.include_router(delete_organization_router)
router.include_router(delete_dataset_router)
router.include_router(delete_resource_router)
