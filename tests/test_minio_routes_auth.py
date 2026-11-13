"""
Authorization tests for the S3 Management routes (``/s3/buckets`` and
``/s3/objects``).

Reading storage (listing, metadata, downloads, presigned downloads) needs the
Endpoint's editor gate. Changing it (creating or deleting a bucket, uploading,
a presigned upload URL, deleting an object) needs the admin gate, so only the
Endpoint's admins can write to its bucket (PASS-261).

The minio routers are only mounted on the main app when S3 is enabled, so these
tests mount them on a minimal standalone app and drive the gates through
``app.dependency_overrides``: when a gate denies, the request is rejected with
403 before the handler runs; when it allows, the request gets past auth and
then fails for an unrelated reason (503, because S3 is not configured here).
"""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.routes.minio_routes.bucket_routes import router as bucket_router
from api.routes.minio_routes.object_routes import router as object_router
from api.services.auth_services import ep_admin_gate, ep_editor_gate

app = FastAPI()
app.include_router(bucket_router)
app.include_router(object_router)
client = TestClient(app)

READS = [
    ("get", "/s3/buckets/", {}),
    ("get", "/s3/buckets/demo", {}),
    ("get", "/s3/objects/demo", {}),
    ("get", "/s3/objects/demo/key/metadata", {}),
    ("post", "/s3/objects/demo/key/presigned-download", {"json": {"expires_in": 3600}}),
    ("get", "/s3/objects/demo/key", {}),
]
WRITES = [
    ("post", "/s3/buckets/", {"json": {"name": "demo"}}),
    ("delete", "/s3/buckets/demo", {}),
    ("post", "/s3/objects/demo", {"files": {"file": ("a.txt", b"x")}}),
    ("post", "/s3/objects/demo/key/presigned-upload", {"json": {"expires_in": 3600}}),
    ("delete", "/s3/objects/demo/key", {}),
]


def _deny():
    raise HTTPException(status_code=403, detail="no")


def _allow():
    return {"username": "u", "sub": "s"}


def _status(method, path, kwargs):
    return getattr(client, method)(path, **kwargs).status_code


def teardown_function():
    app.dependency_overrides.clear()


def test_an_editor_reads_but_cannot_write():
    app.dependency_overrides[ep_editor_gate] = _allow
    app.dependency_overrides[ep_admin_gate] = _deny

    for call in READS:
        assert _status(*call) not in (401, 403), call
    for call in WRITES:
        assert _status(*call) == 403, call


def test_an_admin_writes():
    app.dependency_overrides[ep_admin_gate] = _allow
    app.dependency_overrides[ep_editor_gate] = _deny

    for call in WRITES:
        assert _status(*call) not in (401, 403), call


def test_no_gate_passed_no_access():
    app.dependency_overrides[ep_editor_gate] = _deny
    app.dependency_overrides[ep_admin_gate] = _deny

    for call in READS + WRITES:
        assert _status(*call) == 403, call


def test_every_s3_route_is_covered():
    """A new S3 route has to be added to READS or WRITES above."""
    routes = [
        (method, route.path)
        for router in (bucket_router, object_router)
        for route in router.routes
        for method in route.methods
    ]
    assert len(routes) == len(READS) + len(WRITES) == 11
