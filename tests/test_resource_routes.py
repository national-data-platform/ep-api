# tests/test_resource_routes.py
"""Tests for resource routes."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException


class TestGetResourceById:
    """Tests for get_resource_by_id endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_get_resource_success(self, mock_ckan_settings, mock_services):
        """Test successful resource retrieval."""
        from api.routes.resource_routes.resource_by_id import get_resource_by_id

        mock_services.get_resource.return_value = {
            "id": "res-123",
            "name": "test-resource",
            "url": "https://example.com/data.csv"
        }

        result = await get_resource_by_id(resource_id="res-123", server="local")

        assert result["id"] == "res-123"
        mock_services.get_resource.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_get_resource_pre_ckan_disabled(self, mock_ckan_settings, mock_services):
        """Test get resource with pre_ckan disabled."""
        from api.routes.resource_routes.resource_by_id import get_resource_by_id

        mock_ckan_settings.pre_ckan_enabled = False

        with pytest.raises(HTTPException) as exc_info:
            await get_resource_by_id(resource_id="res-123", server="pre_ckan")

        assert exc_info.value.status_code == 400
        assert "disabled" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.CKANRepository")
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_get_resource_pre_ckan_enabled(
        self, mock_ckan_settings, mock_services, mock_ckan_repo
    ):
        """Test get resource with pre_ckan enabled."""
        from api.routes.resource_routes.resource_by_id import get_resource_by_id

        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan = MagicMock()
        mock_services.get_resource.return_value = {"id": "res-123"}

        result = await get_resource_by_id(resource_id="res-123", server="pre_ckan")

        assert result["id"] == "res-123"

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_get_resource_not_found(self, mock_ckan_settings, mock_services):
        """Test get resource not found."""
        from api.routes.resource_routes.resource_by_id import get_resource_by_id

        mock_services.get_resource.side_effect = Exception("Resource not found")

        with pytest.raises(HTTPException) as exc_info:
            await get_resource_by_id(resource_id="missing", server="local")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_get_resource_generic_error(self, mock_ckan_settings, mock_services):
        """Test get resource generic error."""
        from api.routes.resource_routes.resource_by_id import get_resource_by_id

        mock_services.get_resource.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await get_resource_by_id(resource_id="res-123", server="local")

        assert exc_info.value.status_code == 400


class TestPatchResourceById:
    """Tests for patch_resource_by_id endpoint."""

    @pytest.fixture
    def mock_patch_request(self):
        mock = MagicMock()
        mock.name = "updated-name"
        mock.url = "https://new.example.com/data.csv"
        mock.description = "Updated description"
        mock.format = "csv"
        return mock

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_patch_resource_success(
        self, mock_ckan_settings, mock_services, mock_patch_request
    ):
        """Test successful resource patch."""
        from api.routes.resource_routes.resource_by_id import patch_resource_by_id

        mock_services.patch_resource.return_value = {"id": "res-123", "name": "updated-name"}

        result = await patch_resource_by_id(
            resource_id="res-123",
            data=mock_patch_request,
            server="local",
            _={"user": "test"}
        )

        assert result["id"] == "res-123"
        mock_services.patch_resource.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_patch_resource_pre_ckan_disabled(
        self, mock_ckan_settings, mock_services, mock_patch_request
    ):
        """Test patch resource with pre_ckan disabled."""
        from api.routes.resource_routes.resource_by_id import patch_resource_by_id

        mock_ckan_settings.pre_ckan_enabled = False

        with pytest.raises(HTTPException) as exc_info:
            await patch_resource_by_id(
                resource_id="res-123",
                data=mock_patch_request,
                server="pre_ckan",
                _={"user": "test"}
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.CKANRepository")
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_patch_resource_pre_ckan_enabled(
        self, mock_ckan_settings, mock_services, mock_ckan_repo, mock_patch_request
    ):
        """Test patch resource with pre_ckan enabled."""
        from api.routes.resource_routes.resource_by_id import patch_resource_by_id

        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan = MagicMock()
        mock_services.patch_resource.return_value = {"id": "res-123"}

        result = await patch_resource_by_id(
            resource_id="res-123",
            data=mock_patch_request,
            server="pre_ckan",
            _={"user": "test"}
        )

        assert result["id"] == "res-123"

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_patch_resource_not_found(
        self, mock_ckan_settings, mock_services, mock_patch_request
    ):
        """Test patch resource not found."""
        from api.routes.resource_routes.resource_by_id import patch_resource_by_id

        mock_services.patch_resource.side_effect = Exception("Resource not found")

        with pytest.raises(HTTPException) as exc_info:
            await patch_resource_by_id(
                resource_id="missing",
                data=mock_patch_request,
                server="local",
                _={"user": "test"}
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_patch_resource_generic_error(
        self, mock_ckan_settings, mock_services, mock_patch_request
    ):
        """Test patch resource generic error."""
        from api.routes.resource_routes.resource_by_id import patch_resource_by_id

        mock_services.patch_resource.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await patch_resource_by_id(
                resource_id="res-123",
                data=mock_patch_request,
                server="local",
                _={"user": "test"}
            )

        assert exc_info.value.status_code == 400
        assert "Error updating" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_patch_resource_http_exception(
        self, mock_ckan_settings, mock_services, mock_patch_request
    ):
        """Test patch resource re-raises HTTPException."""
        from api.routes.resource_routes.resource_by_id import patch_resource_by_id

        mock_services.patch_resource.side_effect = HTTPException(
            status_code=403, detail="Forbidden"
        )

        with pytest.raises(HTTPException) as exc_info:
            await patch_resource_by_id(
                resource_id="res-123",
                data=mock_patch_request,
                server="local",
                _={"user": "test"}
            )

        assert exc_info.value.status_code == 403


class TestDeleteResourceById:
    """Tests for delete_resource_by_id endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_delete_resource_success(self, mock_ckan_settings, mock_services):
        """Test successful resource deletion."""
        from api.routes.resource_routes.resource_by_id import delete_resource_by_id

        mock_services.delete_resource.return_value = None

        result = await delete_resource_by_id(
            resource_id="res-123",
            server="local",
            _={"user": "test"}
        )

        assert "deleted successfully" in result["message"]

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_delete_resource_pre_ckan_disabled(self, mock_ckan_settings, mock_services):
        """Test delete resource with pre_ckan disabled."""
        from api.routes.resource_routes.resource_by_id import delete_resource_by_id

        mock_ckan_settings.pre_ckan_enabled = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_resource_by_id(
                resource_id="res-123",
                server="pre_ckan",
                _={"user": "test"}
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.CKANRepository")
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_delete_resource_pre_ckan_enabled(
        self, mock_ckan_settings, mock_services, mock_ckan_repo
    ):
        """Test delete resource with pre_ckan enabled."""
        from api.routes.resource_routes.resource_by_id import delete_resource_by_id

        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan = MagicMock()
        mock_services.delete_resource.return_value = None

        result = await delete_resource_by_id(
            resource_id="res-123",
            server="pre_ckan",
            _={"user": "test"}
        )

        assert "deleted successfully" in result["message"]

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_delete_resource_not_found(self, mock_ckan_settings, mock_services):
        """Test delete resource not found."""
        from api.routes.resource_routes.resource_by_id import delete_resource_by_id

        mock_services.delete_resource.side_effect = Exception("Resource not found")

        with pytest.raises(HTTPException) as exc_info:
            await delete_resource_by_id(
                resource_id="missing",
                server="local",
                _={"user": "test"}
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("api.routes.resource_routes.resource_by_id.dataset_services")
    @patch("api.routes.resource_routes.resource_by_id.ckan_settings")
    async def test_delete_resource_generic_error(self, mock_ckan_settings, mock_services):
        """Test delete resource generic error."""
        from api.routes.resource_routes.resource_by_id import delete_resource_by_id

        mock_services.delete_resource.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await delete_resource_by_id(
                resource_id="res-123",
                server="local",
                _={"user": "test"}
            )

        assert exc_info.value.status_code == 400
