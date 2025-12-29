# tests/repositories/test_base_repository.py
"""
Tests for base repository interface.
"""
import pytest
from typing import Any, Dict, List

from api.repositories.base_repository import DataCatalogRepository


class ConcreteTestRepository(DataCatalogRepository):
    """Concrete implementation of DataCatalogRepository for testing."""

    def __init__(self):
        """Initialize test repository with tracking."""
        self.calls = []

    def package_create(self, **kwargs) -> Dict[str, Any]:
        """Test implementation of package_create."""
        self.calls.append(("package_create", kwargs))
        return {"id": "pkg-123", "name": kwargs.get("name")}

    def package_show(self, id: str) -> Dict[str, Any]:
        """Test implementation of package_show."""
        self.calls.append(("package_show", {"id": id}))
        return {"id": id, "name": "test-package"}

    def package_update(self, **kwargs) -> Dict[str, Any]:
        """Test implementation of package_update."""
        self.calls.append(("package_update", kwargs))
        return {"id": kwargs.get("id"), "name": kwargs.get("name")}

    def package_patch(self, **kwargs) -> Dict[str, Any]:
        """Test implementation of package_patch."""
        self.calls.append(("package_patch", kwargs))
        return {"id": kwargs.get("id"), "title": kwargs.get("title")}

    def package_delete(self, id: str) -> None:
        """Test implementation of package_delete."""
        self.calls.append(("package_delete", {"id": id}))

    def package_search(
        self,
        q: str = "*:*",
        fq: str = "",
        rows: int = 10,
        start: int = 0,
        sort: str = "score desc, metadata_modified desc",
        **kwargs,
    ) -> Dict[str, Any]:
        """Test implementation of package_search."""
        self.calls.append(
            ("package_search", {"q": q, "fq": fq, "rows": rows, "start": start, "sort": sort})
        )
        return {"count": 1, "results": [{"id": "pkg-123"}]}

    def resource_create(self, **kwargs) -> Dict[str, Any]:
        """Test implementation of resource_create."""
        self.calls.append(("resource_create", kwargs))
        return {"id": "res-123", "package_id": kwargs.get("package_id")}

    def resource_show(self, id: str) -> Dict[str, Any]:
        """Test implementation of resource_show."""
        self.calls.append(("resource_show", {"id": id}))
        return {"id": id, "name": "test-resource"}

    def resource_delete(self, id: str) -> None:
        """Test implementation of resource_delete."""
        self.calls.append(("resource_delete", {"id": id}))

    def resource_patch(self, id: str, **kwargs) -> Dict[str, Any]:
        """Test implementation of resource_patch."""
        self.calls.append(("resource_patch", {"id": id, **kwargs}))
        return {"id": id, **kwargs}

    def organization_create(self, **kwargs) -> Dict[str, Any]:
        """Test implementation of organization_create."""
        self.calls.append(("organization_create", kwargs))
        return {"id": "org-123", "name": kwargs.get("name")}

    def organization_show(self, id: str) -> Dict[str, Any]:
        """Test implementation of organization_show."""
        self.calls.append(("organization_show", {"id": id}))
        return {"id": id, "name": "test-org"}

    def organization_list(
        self, all_fields: bool = False, **kwargs
    ) -> List[Dict[str, Any]]:
        """Test implementation of organization_list."""
        self.calls.append(("organization_list", {"all_fields": all_fields}))
        if all_fields:
            return [{"id": "org-123", "name": "test-org"}]
        return ["test-org"]

    def organization_delete(self, id: str) -> None:
        """Test implementation of organization_delete."""
        self.calls.append(("organization_delete", {"id": id}))

    def check_health(self) -> bool:
        """Test implementation of check_health."""
        self.calls.append(("check_health", {}))
        return True


class TestBaseRepositoryInterface:
    """Test that the base repository interface is properly defined."""

    def test_abstract_class_cannot_be_instantiated(self):
        """Test that DataCatalogRepository cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            DataCatalogRepository()

        assert "abstract" in str(exc_info.value).lower()

    def test_concrete_implementation_can_be_instantiated(self):
        """Test that concrete implementations can be instantiated."""
        repo = ConcreteTestRepository()
        assert isinstance(repo, DataCatalogRepository)

    def test_concrete_implementation_has_all_methods(self):
        """Test that concrete implementation has all required methods."""
        repo = ConcreteTestRepository()

        # Verify all abstract methods are implemented
        assert hasattr(repo, "package_create")
        assert hasattr(repo, "package_show")
        assert hasattr(repo, "package_update")
        assert hasattr(repo, "package_patch")
        assert hasattr(repo, "package_delete")
        assert hasattr(repo, "package_search")
        assert hasattr(repo, "resource_create")
        assert hasattr(repo, "resource_show")
        assert hasattr(repo, "resource_delete")
        assert hasattr(repo, "organization_create")
        assert hasattr(repo, "organization_show")
        assert hasattr(repo, "organization_list")
        assert hasattr(repo, "organization_delete")
        assert hasattr(repo, "check_health")


class TestConcreteRepositoryPackageOperations:
    """Test package operations in concrete repository."""

    def test_package_create_with_required_fields(self):
        """Test package creation with required fields."""
        repo = ConcreteTestRepository()
        result = repo.package_create(name="test-package", title="Test Package")

        assert result["id"] == "pkg-123"
        assert result["name"] == "test-package"
        assert ("package_create", {"name": "test-package", "title": "Test Package"}) in repo.calls

    def test_package_show_returns_package_data(self):
        """Test retrieving a package."""
        repo = ConcreteTestRepository()
        result = repo.package_show(id="pkg-123")

        assert result["id"] == "pkg-123"
        assert result["name"] == "test-package"
        assert ("package_show", {"id": "pkg-123"}) in repo.calls

    def test_package_update_with_fields(self):
        """Test updating a package."""
        repo = ConcreteTestRepository()
        result = repo.package_update(id="pkg-123", name="updated-name")

        assert result["id"] == "pkg-123"
        assert result["name"] == "updated-name"
        assert ("package_update", {"id": "pkg-123", "name": "updated-name"}) in repo.calls

    def test_package_patch_partial_update(self):
        """Test patching a package."""
        repo = ConcreteTestRepository()
        result = repo.package_patch(id="pkg-123", title="New Title")

        assert result["id"] == "pkg-123"
        assert result["title"] == "New Title"
        assert ("package_patch", {"id": "pkg-123", "title": "New Title"}) in repo.calls

    def test_package_delete(self):
        """Test deleting a package."""
        repo = ConcreteTestRepository()
        repo.package_delete(id="pkg-123")

        assert ("package_delete", {"id": "pkg-123"}) in repo.calls

    def test_package_search_with_defaults(self):
        """Test searching packages with default parameters."""
        repo = ConcreteTestRepository()
        result = repo.package_search()

        assert result["count"] == 1
        assert len(result["results"]) == 1
        assert ("package_search", {
            "q": "*:*",
            "fq": "",
            "rows": 10,
            "start": 0,
            "sort": "score desc, metadata_modified desc"
        }) in repo.calls

    def test_package_search_with_custom_parameters(self):
        """Test searching packages with custom parameters."""
        repo = ConcreteTestRepository()
        result = repo.package_search(q="test", rows=20, start=10)

        assert result["count"] == 1
        assert ("package_search", {
            "q": "test",
            "fq": "",
            "rows": 20,
            "start": 10,
            "sort": "score desc, metadata_modified desc"
        }) in repo.calls


class TestConcreteRepositoryResourceOperations:
    """Test resource operations in concrete repository."""

    def test_resource_create_with_package_id(self):
        """Test creating a resource."""
        repo = ConcreteTestRepository()
        result = repo.resource_create(package_id="pkg-123", name="test.csv")

        assert result["id"] == "res-123"
        assert result["package_id"] == "pkg-123"
        assert ("resource_create", {"package_id": "pkg-123", "name": "test.csv"}) in repo.calls

    def test_resource_show_returns_resource_data(self):
        """Test retrieving a resource."""
        repo = ConcreteTestRepository()
        result = repo.resource_show(id="res-123")

        assert result["id"] == "res-123"
        assert result["name"] == "test-resource"
        assert ("resource_show", {"id": "res-123"}) in repo.calls

    def test_resource_delete(self):
        """Test deleting a resource."""
        repo = ConcreteTestRepository()
        repo.resource_delete(id="res-123")

        assert ("resource_delete", {"id": "res-123"}) in repo.calls


class TestConcreteRepositoryOrganizationOperations:
    """Test organization operations in concrete repository."""

    def test_organization_create_with_name(self):
        """Test creating an organization."""
        repo = ConcreteTestRepository()
        result = repo.organization_create(name="test-org", title="Test Organization")

        assert result["id"] == "org-123"
        assert result["name"] == "test-org"
        assert ("organization_create", {"name": "test-org", "title": "Test Organization"}) in repo.calls

    def test_organization_show_returns_org_data(self):
        """Test retrieving an organization."""
        repo = ConcreteTestRepository()
        result = repo.organization_show(id="org-123")

        assert result["id"] == "org-123"
        assert result["name"] == "test-org"
        assert ("organization_show", {"id": "org-123"}) in repo.calls

    def test_organization_list_all_fields_true(self):
        """Test listing organizations with full data."""
        repo = ConcreteTestRepository()
        result = repo.organization_list(all_fields=True)

        assert len(result) == 1
        assert result[0]["id"] == "org-123"
        assert result[0]["name"] == "test-org"
        assert ("organization_list", {"all_fields": True}) in repo.calls

    def test_organization_list_all_fields_false(self):
        """Test listing organizations with only names."""
        repo = ConcreteTestRepository()
        result = repo.organization_list(all_fields=False)

        assert result == ["test-org"]
        assert ("organization_list", {"all_fields": False}) in repo.calls

    def test_organization_delete(self):
        """Test deleting an organization."""
        repo = ConcreteTestRepository()
        repo.organization_delete(id="org-123")

        assert ("organization_delete", {"id": "org-123"}) in repo.calls


class TestConcreteRepositoryHealthCheck:
    """Test health check functionality."""

    def test_check_health_returns_true(self):
        """Test health check returns True."""
        repo = ConcreteTestRepository()
        result = repo.check_health()

        assert result is True
        assert ("check_health", {}) in repo.calls
