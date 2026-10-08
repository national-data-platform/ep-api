# tests/repositories/test_mongodb_repository.py
"""
Tests for MongoDB repository implementation.

These tests use mongomock to test the MongoDB repository
without requiring an actual MongoDB server.
"""

import pytest
from mongomock import MongoClient

from api.repositories.mongodb_repository import MongoDBRepository

# Skip all tests if mongomock is not installed
pytest.importorskip("mongomock")


@pytest.fixture
def mongodb_repo(monkeypatch):
    """
    Create a MongoDB repository for testing using mongomock.

    Uses mongomock to create an in-memory MongoDB instance
    that doesn't require a real MongoDB server.
    """
    # Patch MongoClient in the mongodb_repository module to use mongomock
    import api.repositories.mongodb_repository as mongodb_module

    original_client = mongodb_module.MongoClient
    monkeypatch.setattr(mongodb_module, "MongoClient", MongoClient)

    repo = MongoDBRepository(
        connection_string="mongodb://localhost:27017", database_name="test_ndp_catalog"
    )

    # Create a test organization for package tests
    try:
        repo.organization_create(name="test-org", title="Test Organization")
    except Exception:
        pass  # Organization might already exist

    yield repo

    # Cleanup
    repo.client.drop_database("test_ndp_catalog")

    # Restore original MongoClient
    monkeypatch.setattr(mongodb_module, "MongoClient", original_client)


def test_package_create(mongodb_repo):
    """Test creating a package in MongoDB."""
    package = mongodb_repo.package_create(
        name="test-package",
        title="Test Package",
        owner_org="test-org",
        notes="Test description",
        extras=[{"key": "test_key", "value": "test_value"}],
    )

    assert "id" in package
    assert package["name"] == "test-package"
    assert package["title"] == "Test Package"
    # MongoDB repository converts org name to org ID
    assert "owner_org" in package
    assert package["notes"] == "Test description"
    assert len(package["extras"]) == 1
    assert package["extras"][0]["key"] == "test_key"


def test_package_show(mongodb_repo):
    """Test retrieving a package from MongoDB."""
    # Create a package first
    created = mongodb_repo.package_create(
        name="test-show", title="Test Show", owner_org="test-org"
    )

    # Retrieve by ID
    retrieved = mongodb_repo.package_show(created["id"])
    assert retrieved["id"] == created["id"]
    assert retrieved["name"] == "test-show"

    # Retrieve by name
    retrieved_by_name = mongodb_repo.package_show("test-show")
    assert retrieved_by_name["id"] == created["id"]


def test_package_show_not_found(mongodb_repo):
    """Test that retrieving a non-existent package raises an exception."""
    with pytest.raises(Exception, match="not found"):
        mongodb_repo.package_show("non-existent-package")


def test_package_update(mongodb_repo):
    """Test updating a package in MongoDB."""
    # Create a package
    created = mongodb_repo.package_create(
        name="test-update", title="Original Title", owner_org="test-org"
    )

    # Update it
    updated = mongodb_repo.package_update(
        id=created["id"],
        name="test-update",
        title="Updated Title",
        owner_org="test-org",
        notes="Updated notes",
    )

    assert updated["id"] == created["id"]
    assert updated["title"] == "Updated Title"
    assert updated["notes"] == "Updated notes"


def test_package_patch(mongodb_repo):
    """Test partially updating a package in MongoDB."""
    # Create a package
    created = mongodb_repo.package_create(
        name="test-patch",
        title="Original Title",
        owner_org="test-org",
        notes="Original notes",
    )

    # Patch only the title
    patched = mongodb_repo.package_patch(id=created["id"], title="Patched Title")

    assert patched["id"] == created["id"]
    assert patched["title"] == "Patched Title"
    assert patched["notes"] == "Original notes"  # Should remain unchanged


def test_package_delete(mongodb_repo):
    """Test deleting a package from MongoDB."""
    # Create a package
    created = mongodb_repo.package_create(
        name="test-delete", title="To Be Deleted", owner_org="test-org"
    )

    # Delete it
    mongodb_repo.package_delete(created["id"])

    # Verify it's gone
    with pytest.raises(Exception, match="not found"):
        mongodb_repo.package_show(created["id"])


def test_package_search_all(mongodb_repo):
    """Test searching for all packages."""
    # Create some test packages using the existing test-org
    mongodb_repo.package_create(name="pkg1", title="Package One", owner_org="test-org")
    mongodb_repo.package_create(name="pkg2", title="Package Two", owner_org="test-org")
    mongodb_repo.package_create(
        name="pkg3", title="Package Three", owner_org="test-org"
    )

    # Search for all
    results = mongodb_repo.package_search(q="*:*", rows=10)

    assert results["count"] >= 3
    assert len(results["results"]) >= 3


def test_package_search_query(mongodb_repo):
    """Test searching packages with a query."""
    # Create test packages using the existing test-org
    mongodb_repo.package_create(
        name="apple-data", title="Apple Dataset", owner_org="test-org"
    )
    mongodb_repo.package_create(
        name="banana-data", title="Banana Dataset", owner_org="test-org"
    )

    # Search for "apple-data" using field-based query (compatible with mongomock)
    # Note: Simple text queries now use $text operator which mongomock doesn't support
    results = mongodb_repo.package_search(q="name:apple-data", rows=10)

    assert results["count"] >= 1
    assert any(
        "apple" in r["name"].lower() or "apple" in r["title"].lower()
        for r in results["results"]
    )


def test_resource_create(mongodb_repo):
    """Test creating a resource in MongoDB."""
    # Create a package first
    package = mongodb_repo.package_create(
        name="test-pkg-resource", title="Test Package", owner_org="test-org"
    )

    # Create a resource
    resource = mongodb_repo.resource_create(
        package_id=package["id"],
        name="test-resource",
        url="https://example.com/data.csv",
        description="Test resource",
        format="csv",
    )

    assert "id" in resource
    assert resource["package_id"] == package["id"]
    assert resource["name"] == "test-resource"
    assert resource["url"] == "https://example.com/data.csv"


def test_resource_show(mongodb_repo):
    """Test retrieving a resource from MongoDB."""
    # Create package and resource
    package = mongodb_repo.package_create(
        name="test-pkg-show-resource", title="Test Package", owner_org="test-org"
    )
    created_resource = mongodb_repo.resource_create(
        package_id=package["id"],
        name="test-resource",
        url="https://example.com/data.csv",
    )

    # Retrieve the resource
    retrieved = mongodb_repo.resource_show(created_resource["id"])
    assert retrieved["id"] == created_resource["id"]
    assert retrieved["name"] == "test-resource"


def test_resource_delete(mongodb_repo):
    """Test deleting a resource from MongoDB."""
    # Create package and resource
    package = mongodb_repo.package_create(
        name="test-pkg-delete-resource", title="Test Package", owner_org="test-org"
    )
    resource = mongodb_repo.resource_create(
        package_id=package["id"],
        name="test-resource",
        url="https://example.com/data.csv",
    )

    # Delete the resource
    mongodb_repo.resource_delete(resource["id"])

    # Verify it's gone
    with pytest.raises(Exception, match="not found"):
        mongodb_repo.resource_show(resource["id"])


def test_organization_create(mongodb_repo):
    """Test creating an organization in MongoDB."""
    org = mongodb_repo.organization_create(
        name="new-test-org",
        title="New Test Organization",
        description="A test organization",
    )

    assert "id" in org
    assert org["name"] == "new-test-org"
    assert org["title"] == "New Test Organization"
    assert org["description"] == "A test organization"
    # Without creator hashes, the fields stay absent from the doc.
    assert "ndp_user_id" not in org
    assert "ndp_creator_md5" not in org


def test_organization_create_with_creator_hashes(mongodb_repo):
    """When ndp_user_id is provided it is persisted on the org doc."""
    org = mongodb_repo.organization_create(
        name="hashed-test-org",
        title="Hashed Test Org",
        ndp_user_id="abc123def4567890",
        ndp_creator_md5="d41d8cd98f00b204e9800998ecf8427e",
    )

    assert org["ndp_user_id"] == "abc123def4567890"
    assert org["ndp_creator_md5"] == "d41d8cd98f00b204e9800998ecf8427e"
    # Round-trip: the stored doc keeps the fields.
    fetched = mongodb_repo.organization_show(org["id"])
    assert fetched["ndp_user_id"] == "abc123def4567890"
    assert fetched["ndp_creator_md5"] == "d41d8cd98f00b204e9800998ecf8427e"


def test_organization_show(mongodb_repo):
    """Test retrieving an organization from MongoDB."""
    # Create an organization
    created = mongodb_repo.organization_create(name="test-org-show", title="Test Org")

    # Retrieve by ID
    retrieved = mongodb_repo.organization_show(created["id"])
    assert retrieved["id"] == created["id"]

    # Retrieve by name
    retrieved_by_name = mongodb_repo.organization_show("test-org-show")
    assert retrieved_by_name["id"] == created["id"]


def test_organization_list(mongodb_repo):
    """Test listing organizations from MongoDB."""
    # Create some organizations
    mongodb_repo.organization_create(name="org1", title="Organization 1")
    mongodb_repo.organization_create(name="org2", title="Organization 2")

    # List all (names only)
    orgs = mongodb_repo.organization_list(all_fields=False)
    assert len(orgs) >= 2
    assert "org1" in orgs
    assert "org2" in orgs

    # List all (full data)
    orgs_full = mongodb_repo.organization_list(all_fields=True)
    assert len(orgs_full) >= 2
    assert all(isinstance(o, dict) for o in orgs_full)
    assert all("id" in o for o in orgs_full)


def test_organization_delete(mongodb_repo):
    """Test deleting an organization from MongoDB."""
    # Create an organization
    created = mongodb_repo.organization_create(
        name="test-org-delete", title="To Be Deleted"
    )

    # Delete it
    mongodb_repo.organization_delete(created["id"])

    # Verify it's gone
    with pytest.raises(Exception, match="not found"):
        mongodb_repo.organization_show(created["id"])


def test_duplicate_package_name(mongodb_repo):
    """Test that creating a package with a duplicate name raises an error."""
    # Create first package
    mongodb_repo.package_create(
        name="duplicate-name", title="First Package", owner_org="test-org"
    )

    # Try to create another with the same name
    with pytest.raises(Exception, match="already exists"):
        mongodb_repo.package_create(
            name="duplicate-name", title="Second Package", owner_org="test-org"
        )


def test_duplicate_organization_name(mongodb_repo):
    """Test that creating an organization with a duplicate name raises an error."""
    # Create first organization
    mongodb_repo.organization_create(name="duplicate-org", title="First Org")

    # Try to create another with the same name
    with pytest.raises(Exception, match="already exists"):
        mongodb_repo.organization_create(name="duplicate-org", title="Second Org")


def test_resource_patch(mongodb_repo):
    """Test partially updating a resource."""
    package = mongodb_repo.package_create(
        name="test-pkg-patch-res", title="Test Package", owner_org="test-org"
    )
    resource = mongodb_repo.resource_create(
        package_id=package["id"],
        name="original-name",
        url="https://example.com/original.csv",
        format="csv",
    )

    patched = mongodb_repo.resource_patch(id=resource["id"], name="updated-name")

    assert patched["name"] == "updated-name"
    assert patched["url"] == "https://example.com/original.csv"


def test_resource_search_basic(mongodb_repo):
    """Test basic resource search."""
    package = mongodb_repo.package_create(
        name="test-pkg-search-res", title="Test Package", owner_org="test-org"
    )
    mongodb_repo.resource_create(
        package_id=package["id"],
        name="search-resource",
        url="https://example.com/data.csv",
        format="csv",
    )

    results = mongodb_repo.resource_search()
    assert results["count"] >= 1


def test_check_health(mongodb_repo):
    """Test check_health returns True."""
    result = mongodb_repo.check_health()
    assert result is True


def test_package_search_with_fq(mongodb_repo):
    """Test package search with filter query."""
    mongodb_repo.package_create(
        name="fq-test-pkg", title="FQ Test", owner_org="test-org"
    )

    results = mongodb_repo.package_search(fq="owner_org:test-org")
    assert results["count"] >= 1


def test_package_search_with_fq_list(mongodb_repo):
    """Test package search with filter query list."""
    mongodb_repo.package_create(
        name="fq-list-pkg", title="FQ List Test", owner_org="test-org"
    )

    results = mongodb_repo.package_search(fq_list=["owner_org:test-org"])
    assert results["count"] >= 1


def test_resource_search_by_name(mongodb_repo):
    """Test resource search by name."""
    package = mongodb_repo.package_create(
        name="test-pkg-res-name", title="Test Package", owner_org="test-org"
    )
    mongodb_repo.resource_create(
        package_id=package["id"],
        name="unique-name-xyz",
        url="https://example.com/data.csv",
        format="csv",
    )

    results = mongodb_repo.resource_search(name="unique-name")
    assert results["count"] >= 1


def test_resource_search_by_format(mongodb_repo):
    """Test resource search by format."""
    package = mongodb_repo.package_create(
        name="test-pkg-res-format", title="Test Package", owner_org="test-org"
    )
    mongodb_repo.resource_create(
        package_id=package["id"],
        name="json-resource",
        url="https://example.com/data.json",
        format="json",
    )

    results = mongodb_repo.resource_search(format="json")
    assert results["count"] >= 1


def test_resource_search_by_query(mongodb_repo):
    """Test resource search with query."""
    package = mongodb_repo.package_create(
        name="test-pkg-res-query", title="Test Package", owner_org="test-org"
    )
    mongodb_repo.resource_create(
        package_id=package["id"],
        name="weather-data",
        url="https://example.com/weather.csv",
        description="Weather data",
        format="csv",
    )

    results = mongodb_repo.resource_search(query="weather")
    assert results["count"] >= 1


def test_resource_search_by_url(mongodb_repo):
    """Test resource search by URL."""
    package = mongodb_repo.package_create(
        name="test-pkg-res-url", title="Test Package", owner_org="test-org"
    )
    mongodb_repo.resource_create(
        package_id=package["id"],
        name="url-resource",
        url="https://unique-domain.example.org/data.csv",
        format="csv",
    )

    results = mongodb_repo.resource_search(url="unique-domain")
    assert results["count"] >= 1


def test_resource_search_by_description(mongodb_repo):
    """Test resource search by description."""
    package = mongodb_repo.package_create(
        name="test-pkg-res-desc", title="Test Package", owner_org="test-org"
    )
    mongodb_repo.resource_create(
        package_id=package["id"],
        name="desc-resource",
        url="https://example.com/data.csv",
        description="unique-description-xyz",
        format="csv",
    )

    results = mongodb_repo.resource_search(description="unique-description")
    assert results["count"] >= 1


def test_package_create_invalid_org(mongodb_repo):
    """Test package create with invalid org."""
    with pytest.raises(Exception, match="Organization does not exist"):
        mongodb_repo.package_create(
            name="invalid-org-pkg", title="Test", owner_org="non-existent-org"
        )


def test_package_update_no_id(mongodb_repo):
    """Test package update without ID."""
    with pytest.raises(Exception, match="Package ID is required"):
        mongodb_repo.package_update(title="New Title")


def test_resource_create_no_package(mongodb_repo):
    """Test resource create without package_id."""
    with pytest.raises(Exception, match="package_id is required"):
        mongodb_repo.resource_create(name="orphan", url="https://example.com")


def test_package_create_keeps_tags_groups_privacy_licence_and_version(mongodb_repo):
    """These were dropped on create, unlike in CKAN (issue #311)."""
    created = mongodb_repo.package_create(
        name="full-package",
        title="Full Package",
        owner_org="test-org",
        tags=[{"name": "oceanography"}, {"name": "climate"}],
        groups=[{"name": "research"}],
        private=True,
        license_id="cc-by",
        version="2.0",
    )

    stored = mongodb_repo.package_show(created["id"])

    assert stored["tags"] == [{"name": "oceanography"}, {"name": "climate"}]
    assert stored["groups"] == [{"name": "research"}]
    assert stored["private"] is True
    assert stored["license_id"] == "cc-by"
    assert stored["version"] == "2.0"


def test_package_create_defaults_match_ckan(mongodb_repo):
    created = mongodb_repo.package_create(
        name="bare-package", title="Bare", owner_org="test-org"
    )

    stored = mongodb_repo.package_show(created["id"])

    assert stored["tags"] == []
    assert stored["groups"] == []
    assert stored["private"] is False
    assert "license_id" not in stored
    assert "version" not in stored


class _FakeCollection:
    """Just enough of a collection to watch the text index being managed."""

    def __init__(self, indexes):
        self.indexes = dict(indexes)
        self.dropped = []

    def index_information(self):
        return self.indexes

    def drop_index(self, name):
        self.dropped.append(name)
        self.indexes.pop(name)

    def create_index(self, keys, weights=None, name=None):
        if name in self.indexes and self.indexes[name]["weights"] != weights:
            raise Exception("IndexKeySpecsConflict")  # what MongoDB does
        self.indexes[name] = {"weights": weights}


def _ensure_on(collection):
    repo = MongoDBRepository.__new__(MongoDBRepository)
    repo.packages = collection
    repo._ensure_fulltext_index()


def test_an_index_built_on_tags_is_replaced_by_one_on_tag_names():
    """An existing catalog has the old index; it must still start (issue #311)."""
    old = {"weights": {"title": 10, "tags": 5, "notes": 1}}
    collection = _FakeCollection({"fulltext_search_index": old})

    _ensure_on(collection)

    assert collection.dropped == ["fulltext_search_index"]
    assert collection.indexes["fulltext_search_index"]["weights"] == {
        "title": 10,
        "tags.name": 5,
        "notes": 1,
    }


def test_a_current_index_is_left_alone():
    current = {"weights": {"title": 10, "tags.name": 5, "notes": 1}}
    collection = _FakeCollection({"fulltext_search_index": current})

    _ensure_on(collection)

    assert collection.dropped == []
