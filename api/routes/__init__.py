from .default_routes import router as default_router  # noqa: F401
from .delete_routes import router as delete_router  # noqa: F401
from .health_routes import router as health_router  # noqa: F401
from .redirect_routes import router as redirect_router  # noqa: F401
from .register_routes import router as register_router  # noqa: F401
from .resource_routes.resource_by_id import router as resource_router  # noqa: F401
from .resource_routes.search_resources import (  # noqa: F401
    router as resource_search_router,
)
from .search_routes import router as search_router  # noqa: F401
from .status_routes import router as status_router  # noqa: F401
from .update_routes import router as update_router  # noqa: F401
from .user_routes import router as user_router  # noqa: F401
from .minio_routes.bucket_routes import router as minio_bucket_router  # noqa: F401
from .minio_routes.object_routes import router as minio_object_router  # noqa: F401
