# tests/repositories/test_ckan_repository.py
"""
Tests for CKAN repository implementation.
"""
import pytest
from unittest.mock import MagicMock

from api.repositories.ckan_repository import CKANRepository


class TestCKANRepositoryPackageOperations:
    """Test package operations in CKAN repository."""

    def test_package_create(self):
        """Test creating a package."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_create.return_value = {"id": "pkg-123", "name": "test"}

        repo = CKANRepository(mock_ckan)
        result = repo.package_create(name="test", title="Test Package")

        assert result == {"id": "pkg-123", "name": "test"}
        mock_ckan.action.package_create.assert_called_once_with(
            name="test", title="Test Package"
        )

    def test_package_show(self):
        """Test retrieving a package."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {"id": "pkg-123", "name": "test"}

        repo = CKANRepository(mock_ckan)
        result = repo.package_show(id="pkg-123")

        assert result == {"id": "pkg-123", "name": "test"}
        mock_ckan.action.package_show.assert_called_once_with(id="pkg-123")

    def test_package_update(self):
        """Test updating a package."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_update.return_value = {
            "id": "pkg-123",
            "title": "Updated",
        }

        repo = CKANRepository(mock_ckan)
        result = repo.package_update(id="pkg-123", title="Updated")

        assert result == {"id": "pkg-123", "title": "Updated"}
        mock_ckan.action.package_update.assert_called_once_with(
            id="pkg-123", title="Updated"
        )

    def test_package_patch(self):
        """Test patching a package."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_patch.return_value = {
            "id": "pkg-123",
            "title": "Patched",
        }

        repo = CKANRepository(mock_ckan)
        result = repo.package_patch(id="pkg-123", title="Patched")

        assert result == {"id": "pkg-123", "title": "Patched"}
        mock_ckan.action.package_patch.assert_called_once_with(
            id="pkg-123", title="Patched"
        )

    def test_package_delete(self):
        """Test deleting a package (uses dataset_purge for permanent deletion)."""
        mock_ckan = MagicMock()
        mock_ckan.action.dataset_purge.return_value = None

        repo = CKANRepository(mock_ckan)
        repo.package_delete(id="pkg-123")

        mock_ckan.action.dataset_purge.assert_called_once_with(id="pkg-123")

    def test_package_search(self):
        """Test searching packages."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_search.return_value = {
            "count": 1,
            "results": [{"id": "pkg-123"}],
        }

        repo = CKANRepository(mock_ckan)
        result = repo.package_search(q="test", rows=10)

        assert result == {"count": 1, "results": [{"id": "pkg-123"}]}
        mock_ckan.action.package_search.assert_called_once()


class TestCKANRepositoryResourceOperations:
    """Test resource operations in CKAN repository."""

    def test_resource_create(self):
        """Test creating a resource."""
        mock_ckan = MagicMock()
        mock_ckan.action.resource_create.return_value = {
            "id": "res-123",
            "name": "test.csv",
        }

        repo = CKANRepository(mock_ckan)
        result = repo.resource_create(package_id="pkg-123", name="test.csv")

        assert result == {"id": "res-123", "name": "test.csv"}
        mock_ckan.action.resource_create.assert_called_once_with(
            package_id="pkg-123", name="test.csv"
        )

    def test_resource_show(self):
        """Test retrieving a resource."""
        mock_ckan = MagicMock()
        mock_ckan.action.resource_show.return_value = {
            "id": "res-123",
            "name": "test.csv",
        }

        repo = CKANRepository(mock_ckan)
        result = repo.resource_show(id="res-123")

        assert result == {"id": "res-123", "name": "test.csv"}
        mock_ckan.action.resource_show.assert_called_once_with(id="res-123")

    def test_resource_delete(self):
        """Test deleting a resource."""
        mock_ckan = MagicMock()
        mock_ckan.action.resource_delete.return_value = None

        repo = CKANRepository(mock_ckan)
        repo.resource_delete(id="res-123")

        mock_ckan.action.resource_delete.assert_called_once_with(id="res-123")


class TestCKANRepositoryOrganizationOperations:
    """Test organization operations in CKAN repository."""

    def test_organization_create(self):
        """Test creating an organization."""
        mock_ckan = MagicMock()
        mock_ckan.action.organization_create.return_value = {
            "id": "org-123",
            "name": "test-org",
        }

        repo = CKANRepository(mock_ckan)
        result = repo.organization_create(name="test-org", title="Test Org")

        assert result == {"id": "org-123", "name": "test-org"}
        mock_ckan.action.organization_create.assert_called_once_with(
            name="test-org", title="Test Org"
        )

    def test_organization_show(self):
        """Test retrieving an organization."""
        mock_ckan = MagicMock()
        mock_ckan.action.organization_show.return_value = {
            "id": "org-123",
            "name": "test-org",
        }

        repo = CKANRepository(mock_ckan)
        result = repo.organization_show(id="org-123")

        assert result == {"id": "org-123", "name": "test-org"}
        mock_ckan.action.organization_show.assert_called_once_with(id="org-123")

    def test_organization_list(self):
        """Test listing organizations."""
        mock_ckan = MagicMock()
        mock_ckan.action.organization_list.return_value = [
            {"id": "org-123", "name": "test-org"}
        ]

        repo = CKANRepository(mock_ckan)
        result = repo.organization_list(all_fields=True)

        assert result == [{"id": "org-123", "name": "test-org"}]
        mock_ckan.action.organization_list.assert_called_once_with(all_fields=True)

    def test_organization_delete(self):
        """Test deleting an organization (uses organization_purge for permanent deletion)."""
        mock_ckan = MagicMock()
        mock_ckan.action.organization_purge.return_value = None

        repo = CKANRepository(mock_ckan)
        repo.organization_delete(id="org-123")

        mock_ckan.action.organization_purge.assert_called_once_with(id="org-123")


class TestCKANRepositoryHealth:
    """Test health check functionality."""

    def test_check_health_success(self):
        """Test successful health check."""
        mock_ckan = MagicMock()
        mock_ckan.action.status_show.return_value = {"version": "2.9"}

        repo = CKANRepository(mock_ckan)
        result = repo.check_health()

        assert result is True
        mock_ckan.action.status_show.assert_called_once()

    def test_check_health_failure(self):
        """Test health check when CKAN is unreachable."""
        mock_ckan = MagicMock()
        mock_ckan.action.status_show.side_effect = Exception("Connection failed")

        repo = CKANRepository(mock_ckan)
        result = repo.check_health()

        assert result is False


class TestCKANRepositoryInitialization:
    """Test repository initialization."""

    def test_init_stores_ckan_instance(self):
        """Test that initialization stores the CKAN instance."""
        mock_ckan = MagicMock()

        repo = CKANRepository(mock_ckan)

        assert repo.ckan is mock_ckan
