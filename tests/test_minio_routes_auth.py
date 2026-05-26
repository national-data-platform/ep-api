"""
Authorization tests for the S3 Management routes (``/s3/buckets`` and
``/s3/objects``).

These endpoints back the S3 Management tool, which is an administrative storage
feature. They must be guarded by :func:`get_user_for_write_operation` so that
viewers and users with no role cannot reach them — mirroring the UI, which only
shows the S3 Management entry to writers.

The minio routers are only mounted on the main app when S3 is enabled, so these
tests mount them on a minimal standalone app and drive the guard through
``app.dependency_overrides``. That isolates exactly what we want to verify (the
routers require write permission) without needing a configured MinIO backend:
when the guard denies, the request is rejected with 403 before the handler runs;
when it allows, the request gets past auth and then fails for an unrelated
reason (503, because S3 is not configured in the test environment).
"""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.routes.minio_routes.bucket_routes import router as bucket_router
from api.routes.minio_routes.object_routes import router as object_router
from api.services.auth_services import get_user_for_write_operation

app = FastAPI()
app.include_router(bucket_router)
app.include_router(object_router)
client = TestClient(app)

# (method, path, kwargs) for every S3 Management endpoint.
S3_MANAGEMENT_ENDPOINTS = [
    ("post", "/s3/buckets/", {"json": {"name": "demo"}}),
    ("get", "/s3/buckets/", {}),
    ("get", "/s3/buckets/demo", {}),
    ("delete", "/s3/buckets/demo", {}),
    ("post", "/s3/objects/demo", {"files": {"file": ("a.txt", b"x")}}),
    ("get", "/s3/objects/demo", {}),
    ("get", "/s3/objects/demo/key/metadata", {}),
    ("post", "/s3/objects/demo/key/presigned-upload", {"json": {"expires_in": 3600}}),
    ("post", "/s3/objects/demo/key/presigned-download", {"json": {"expires_in": 3600}}),
    ("get", "/s3/objects/demo/key", {}),
    ("delete", "/s3/objects/demo/key", {}),
]


def teardown_function():
    app.dependency_overrides.clear()


def test_s3_management_denies_users_without_write_permission():
    """Every S3 Management endpoint returns 403 when the write guard denies."""

    def _deny():
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify resources.",
        )

    app.dependency_overrides[get_user_for_write_operation] = _deny

    for method, path, kwargs in S3_MANAGEMENT_ENDPOINTS:
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 403, (
            f"{method.upper()} {path} should be writer-only "
            f"but returned {response.status_code}"
        )


def test_s3_management_allows_writers_past_the_guard():
    """A writer passes the guard (the call then fails for an unrelated reason,
    not 401/403)."""

    app.dependency_overrides[get_user_for_write_operation] = lambda: {
        "username": "writer-user",
        "sub": "writer-sub",
        "effective_role": "writer",
    }

    for method, path, kwargs in S3_MANAGEMENT_ENDPOINTS:
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code not in (401, 403), (
            f"{method.upper()} {path} should let a writer past auth "
            f"but returned {response.status_code}"
        )
