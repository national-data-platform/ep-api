"""
Authorization tests for the delete routes (``DELETE /resource``,
``DELETE /resource/{name}``, ``DELETE /organization/{name}`` and
``DELETE /dataset/{id}/resource/{resource_id}``).

These endpoints remove datasets, resources and whole organizations, so they
must be guarded by :func:`get_user_for_write_operation` like every other write
route. They were reachable without any token at all.

The tests send real HTTP requests through a minimal app with the delete router
mounted, so they exercise FastAPI's dependency injection rather than calling
the handlers directly — which is how the missing guard went unnoticed.
"""

from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.routes.delete_routes import router as delete_router
from api.services.auth_services import get_user_for_write_operation

app = FastAPI()
app.include_router(delete_router)
client = TestClient(app)

# (method, path) for every delete endpoint.
DELETE_ENDPOINTS = [
    ("delete", "/resource?resource_id=some-id"),
    ("delete", "/resource/some-dataset"),
    ("delete", "/organization/some-org"),
    ("delete", "/dataset/some-dataset/resource/some-resource"),
]


def teardown_function():
    app.dependency_overrides.clear()


@patch("api.routes.delete_routes.delete_resource_from_dataset.dataset_services")
@patch("api.routes.delete_routes.delete_organization_route.organization_services")
@patch("api.routes.delete_routes.delete_dataset.dataset_services")
def test_delete_routes_reject_requests_without_a_token(
    mock_dataset_services, mock_org_services, mock_resource_services
):
    """No Authorization header means 401, and nothing is deleted."""
    for method, path in DELETE_ENDPOINTS:
        response = getattr(client, method)(path)
        assert response.status_code == 401, (
            f"{method.upper()} {path} should require a token "
            f"but returned {response.status_code}"
        )

    mock_dataset_services.delete_dataset.assert_not_called()
    mock_org_services.delete_organization.assert_not_called()
    mock_resource_services.delete_resource.assert_not_called()


@patch("api.routes.delete_routes.delete_resource_from_dataset.dataset_services")
@patch("api.routes.delete_routes.delete_organization_route.organization_services")
@patch("api.routes.delete_routes.delete_dataset.dataset_services")
def test_delete_routes_deny_users_without_write_permission(
    mock_dataset_services, mock_org_services, mock_resource_services
):
    """Every delete endpoint returns 403 when the write guard denies."""

    def _deny():
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify resources.",
        )

    app.dependency_overrides[get_user_for_write_operation] = _deny

    for method, path in DELETE_ENDPOINTS:
        response = getattr(client, method)(path)
        assert response.status_code == 403, (
            f"{method.upper()} {path} should be writer-only "
            f"but returned {response.status_code}"
        )

    mock_dataset_services.delete_dataset.assert_not_called()
    mock_org_services.delete_organization.assert_not_called()
    mock_resource_services.delete_resource.assert_not_called()


@patch("api.routes.delete_routes.delete_resource_from_dataset.dataset_services")
@patch("api.routes.delete_routes.delete_organization_route.organization_services")
@patch("api.routes.delete_routes.delete_dataset.dataset_services")
def test_delete_routes_allow_writers(
    mock_dataset_services, mock_org_services, mock_resource_services
):
    """A writer passes the guard and the delete goes through."""
    app.dependency_overrides[get_user_for_write_operation] = lambda: {
        "username": "writer-user",
        "sub": "writer-sub",
        "effective_role": "writer",
    }

    for method, path in DELETE_ENDPOINTS:
        response = getattr(client, method)(path)
        assert response.status_code == 200, (
            f"{method.upper()} {path} should succeed for a writer "
            f"but returned {response.status_code}"
        )

    assert mock_dataset_services.delete_dataset.call_count == 2
    mock_org_services.delete_organization.assert_called_once()
    mock_resource_services.delete_resource.assert_called_once()
