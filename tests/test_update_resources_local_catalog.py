# tests/test_update_resources_local_catalog.py
"""
Updating URL, S3 and Kafka resources must go to the configured local catalog.

Creating them already used ``catalog_settings.local_catalog`` (CKAN or
MongoDB), but the PUT/PATCH routes passed ``ckan_settings.ckan`` to the
services, so on a MongoDB-backed Endpoint every update was sent to CKAN and
failed (issue #343).
"""

import copy
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from fastapi.testclient import TestClient

from api.config import catalog_settings, ckan_settings
from api.main import app
from api.services.auth_services import get_user_for_write_operation

client = TestClient(app)


class FakeLocalCatalog:
    """In-memory stand-in for a non-CKAN local catalog such as MongoDB."""

    def __init__(self, package):
        self.packages = {package["id"]: copy.deepcopy(package)}

    def package_show(self, id):
        if id not in self.packages:
            raise Exception(f"Package '{id}' not found")
        return copy.deepcopy(self.packages[id])

    def package_update(self, **kwargs):
        package = {**self.packages[kwargs["id"]], **kwargs}
        self.packages[kwargs["id"]] = package
        return copy.deepcopy(package)

    def package_patch(self, **kwargs):
        return self.package_update(**kwargs)

    def resource_show(self, id):
        for package in self.packages.values():
            for resource in package.get("resources", []):
                if resource["id"] == id:
                    return copy.deepcopy(resource)
        raise Exception(f"Resource '{id}' not found")

    def resource_patch(self, **kwargs):
        resource_id = kwargs.pop("id")
        for package in self.packages.values():
            for resource in package.get("resources", []):
                if resource["id"] == resource_id:
                    resource.update(kwargs)
                    return copy.deepcopy(resource)
        raise Exception(f"Resource '{resource_id}' not found")


def _package(extras, resource_format, resource_url):
    return {
        "id": "pkg-1",
        "name": "pkg-one",
        "title": "Before",
        "owner_org": "org-1",
        "notes": "notes",
        "extras": [{"key": k, "value": v} for k, v in extras.items()],
        "resources": [{"id": "res-1", "format": resource_format, "url": resource_url}],
    }


@pytest.fixture
def local_catalog_only():
    """A local catalog that is not CKAN, and a CKAN that must not be called."""

    def use(package):
        fake = FakeLocalCatalog(package)
        ckan = MagicMock()
        ckan.action.package_show.side_effect = AssertionError("CKAN was called")
        ckan.action.package_update.side_effect = AssertionError("CKAN was called")
        patches = [
            patch.object(
                type(catalog_settings),
                "local_catalog",
                new_callable=PropertyMock,
                return_value=fake,
            ),
            patch.object(
                type(ckan_settings),
                "ckan",
                new_callable=PropertyMock,
                return_value=ckan,
            ),
        ]
        for p in patches:
            p.start()
        started.extend(patches)
        return fake

    started = []
    app.dependency_overrides[get_user_for_write_operation] = lambda: {
        "username": "writer",
        "roles": ["ndp_writer"],
    }
    yield use
    for p in started:
        p.stop()
    app.dependency_overrides.clear()


@pytest.mark.parametrize("method", ["put", "patch"])
def test_url_update_goes_to_the_local_catalog(local_catalog_only, method):
    fake = local_catalog_only(
        _package({"file_type": "CSV"}, "url", "https://example.org/a.csv")
    )

    response = getattr(client, method)(
        "/url/pkg-1",
        json={
            "resource_title": "After",
            "resource_url": "https://example.org/b.csv",
        },
    )

    assert response.status_code == 200, response.text
    stored = fake.packages["pkg-1"]
    assert stored["title"] == "After"
    assert stored["resources"][0]["url"] == "https://example.org/b.csv"


@pytest.mark.parametrize("method", ["put", "patch"])
def test_s3_update_goes_to_the_local_catalog(local_catalog_only, method):
    fake = local_catalog_only(_package({}, "s3", "s3://bucket/a.csv"))

    response = getattr(client, method)("/s3/pkg-1", json={"resource_title": "After"})

    assert response.status_code == 200, response.text
    assert fake.packages["pkg-1"]["title"] == "After"


@pytest.mark.parametrize("method", ["put", "patch"])
def test_kafka_update_goes_to_the_local_catalog(local_catalog_only, method):
    fake = local_catalog_only(
        _package(
            {"host": "kafka", "port": "9092", "topic": "old"},
            "kafka",
            "kafka://kafka:9092/old",
        )
    )

    response = getattr(client, method)(
        "/kafka/pkg-1", json={"dataset_title": "After", "kafka_topic": "new"}
    )

    assert response.status_code == 200, response.text
    stored = fake.packages["pkg-1"]
    assert stored["title"] == "After"
    assert {"key": "topic", "value": "new"} in stored["extras"]
