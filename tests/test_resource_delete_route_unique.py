"""
``DELETE /resource/{...}`` must be registered exactly once.

``delete_routes`` (dataset by name) and ``resource_routes`` (resource by id)
both used to declare it. Starlette matches the first route registered, so the
second was never reached: deleting a resource by its id answered 404 and left
it in place, while the OpenAPI schema documented the operation (#299).
"""

import re

from fastapi import FastAPI

from api.routes.delete_routes import router as delete_router
from api.routes.resource_routes.resource_by_id import router as resource_router


def test_delete_resource_by_path_is_registered_once():
    app = FastAPI()
    # Same order as api/main.py.
    app.include_router(delete_router)
    app.include_router(resource_router)

    # Normalise the parameter name: /resource/{resource_name} and
    # /resource/{resource_id} are the same pattern to the router.
    paths = [
        path
        for path, operations in app.openapi()["paths"].items()
        if "delete" in operations and re.sub(r"\{[^}]+\}", "{}", path) == "/resource/{}"
    ]

    assert paths == ["/resource/{resource_name}"]
