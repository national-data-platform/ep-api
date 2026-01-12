# tests/test_delete_routes.py
"""Tests for delete routes."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException


class TestDeleteResourceRoute:
    """Tests for delete_resource endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_resource_success(self, mock_ckan_settings, mock_services):
        """Test successful resource deletion."""
        from api.routes.delete_routes.delete_dataset import delete_resource

        mock_services.delete_dataset.return_value = None

        result = await delete_resource(resource_id="res-123", server="local")

        assert result["message"] == "res-123 deleted successfully"
        mock_services.delete_dataset.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_resource_pre_ckan_disabled(
        self, mock_ckan_settings, mock_services
    ):
        """Test delete with pre_ckan server when disabled."""
        from api.routes.delete_routes.delete_dataset import delete_resource

        mock_ckan_settings.pre_ckan_enabled = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_resource(resource_id="res-123", server="pre_ckan")

        assert exc_info.value.status_code == 400
        assert "disabled" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.CKANRepository")
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_resource_pre_ckan_enabled(
        self, mock_ckan_settings, mock_services, mock_ckan_repo
    ):
        """Test delete with pre_ckan server when enabled."""
        from api.routes.delete_routes.delete_dataset import delete_resource

        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan = MagicMock()
        mock_services.delete_dataset.return_value = None

        result = await delete_resource(resource_id="res-123", server="pre_ckan")

        assert result["message"] == "res-123 deleted successfully"

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_resource_not_found(self, mock_ckan_settings, mock_services):
        """Test delete with resource not found."""
        from api.routes.delete_routes.delete_dataset import delete_resource

        mock_services.delete_dataset.side_effect = Exception("Resource not found")

        with pytest.raises(HTTPException) as exc_info:
            await delete_resource(resource_id="res-123", server="local")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_resource_no_scheme(self, mock_ckan_settings, mock_services):
        """Test delete with No scheme supplied error."""
        from api.routes.delete_routes.delete_dataset import delete_resource

        mock_services.delete_dataset.side_effect = Exception("No scheme supplied")

        with pytest.raises(HTTPException) as exc_info:
            await delete_resource(resource_id="res-123", server="local")

        assert exc_info.value.status_code == 400
        assert "not configured" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_resource_generic_error(
        self, mock_ckan_settings, mock_services
    ):
        """Test delete with generic error."""
        from api.routes.delete_routes.delete_dataset import delete_resource

        mock_services.delete_dataset.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await delete_resource(resource_id="res-123", server="local")

        assert exc_info.value.status_code == 400
        assert "Database error" in exc_info.value.detail


class TestDeleteResourceByNameRoute:
    """Tests for delete_resource_by_name endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_by_name_success(self, mock_ckan_settings, mock_services):
        """Test successful resource deletion by name."""
        from api.routes.delete_routes.delete_dataset import delete_resource_by_name

        mock_services.delete_dataset.return_value = None

        result = await delete_resource_by_name(
            resource_name="my-resource", server="local"
        )

        assert result["message"] == "my-resource deleted successfully"
        mock_services.delete_dataset.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_by_name_pre_ckan_disabled(
        self, mock_ckan_settings, mock_services
    ):
        """Test delete by name with pre_ckan disabled."""
        from api.routes.delete_routes.delete_dataset import delete_resource_by_name

        mock_ckan_settings.pre_ckan_enabled = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_resource_by_name(
                resource_name="my-resource", server="pre_ckan"
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.CKANRepository")
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_by_name_pre_ckan_enabled(
        self, mock_ckan_settings, mock_services, mock_ckan_repo
    ):
        """Test delete by name with pre_ckan enabled."""
        from api.routes.delete_routes.delete_dataset import delete_resource_by_name

        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan = MagicMock()
        mock_services.delete_dataset.return_value = None

        result = await delete_resource_by_name(
            resource_name="my-resource", server="pre_ckan"
        )

        assert result["message"] == "my-resource deleted successfully"

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_by_name_not_found(self, mock_ckan_settings, mock_services):
        """Test delete by name with resource not found."""
        from api.routes.delete_routes.delete_dataset import delete_resource_by_name

        mock_services.delete_dataset.side_effect = Exception("not found")

        with pytest.raises(HTTPException) as exc_info:
            await delete_resource_by_name(resource_name="missing", server="local")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("api.routes.delete_routes.delete_dataset.dataset_services")
    @patch("api.routes.delete_routes.delete_dataset.ckan_settings")
    async def test_delete_by_name_no_scheme(self, mock_ckan_settings, mock_services):
        """Test delete by name with No scheme supplied error."""
        from api.routes.delete_routes.delete_dataset import delete_resource_by_name

        mock_services.delete_dataset.side_effect = Exception("No scheme supplied")

        with pytest.raises(HTTPException) as exc_info:
            await delete_resource_by_name(resource_name="my-resource", server="local")

        assert exc_info.value.status_code == 400
        assert "not configured" in exc_info.value.detail.lower()
