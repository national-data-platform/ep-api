"""
The bundled S3 service has to be an image an operator can actually pull.

`minio/minio` was deleted from Docker Hub in September 2026 and quay.io
stopped serving it anonymously days later, so every installation that enabled
S3 failed — after CKAN had been installed and the `.env` written, wasting the
whole run (issue #293). No tag survived, so nothing could be pinned back to.

These guard the shape of the replacement rather than the registry, which no
test here can reach: a drop-in fork is only drop-in while it is still invoked
like the thing it replaces.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

COMPOSE = Path(__file__).resolve().parents[1] / "docker-compose.yml"

# Registries that no longer serve MinIO to an unauthenticated puller. Written
# as a list because the second one was the fix for the first, for a fortnight.
WITHDRAWN = ("minio/minio", "quay.io/minio/minio")


@pytest.fixture(scope="module")
def s3_service():
    config = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    service = config["services"]["minio"]
    assert service, "the compose file has no S3 service"
    return service


def test_the_image_is_one_that_can_still_be_pulled(s3_service):
    """The regression: someone restoring the old image in a tidy-up."""
    image = s3_service["image"]

    for withdrawn in WITHDRAWN:
        assert not image.startswith(withdrawn), (
            "%s cannot be pulled without credentials; see issue #293" % image
        )


def test_the_image_is_pinned(s3_service):
    """
    An image outside our control disappeared from under installations. A
    moving tag would mean the next change arrives the same way.
    """
    image = s3_service["image"]

    assert ":" in image, "the S3 image has no tag at all: " + image
    assert not image.endswith(":latest"), "the S3 image is unpinned: " + image


def test_the_server_is_still_invoked_the_way_minio_was(s3_service):
    """
    The replacement is a fork that keeps MinIO's interface. That is what
    makes it a one-line change, and it stops being true the moment the
    command or the credentials are renamed.
    """
    environment = s3_service["environment"]
    keys = (
        environment
        if isinstance(environment, dict)
        else dict(item.split("=", 1) for item in environment)
    )

    assert "MINIO_ROOT_USER" in keys
    assert "MINIO_ROOT_PASSWORD" in keys
    assert "server" in s3_service["command"]
