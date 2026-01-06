# tests/test_register_routes.py
"""Tests for register routes."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException


class TestCreateServiceRoute:
    """Tests for create_service endpoint."""

    @pytest.fixture
    def mock_service_request(self):
        """Create a mock ServiceRequest."""
        mock = MagicMock()
        mock.service_name = "test-service"
        mock.service_title = "Test Service"
        mock.owner_org = "services"
        mock.service_url = "https://example.com/api"
        mock.service_type = "API"
        mock.notes = "Test notes"
        mock.extras = {}
        mock.health_check_url = "https://example.com/health"
        mock.documentation_url = "https://docs.example.com"
        return mock

    @pytest.mark.asyncio
    @patch("api.routes.register_routes.post_service.add_service")
    @patch("api.routes.register_routes.post_service.catalog_settings")
    @patch("api.routes.register_routes.post_service.ckan_settings")
    async def test_create_service_local_success(
        self, mock_ckan_settings, mock_catalog_settings, mock_add_service, mock_service_request
    ):
        """Test successful service creation on local."""
        from api.routes.register_routes.post_service import create_service
        from api.repositories import CKANRepository

        mock_repo = MagicMock(spec=CKANRepository)
        mock_repo.ckan = MagicMock()
        mock_catalog_settings.local_catalog = mock_repo
        mock_add_service.return_value = "service-123"

        result = await create_service(
            data=mock_service_request,
            server="local",
            user_info={"user": "test"}
        )

        assert result["id"] == "service-123"
        mock_add_service.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routes.register_routes.post_service.add_service")
    @patch("api.routes.register_routes.post_service.catalog_settings")
    @patch("api.routes.register_routes.post_service.ckan_settings")
    async def test_create_service_pre_ckan_disabled(
        self, mock_ckan_settings, mock_catalog_settings, mock_add_service, mock_service_request
    ):
        """Test create service with pre_ckan disabled."""
        from api.routes.register_routes.post_service import create_service

        mock_ckan_settings.pre_ckan_enabled = False

        with pytest.raises(HTTPException) as exc_info:
            await create_service(
                data=mock_service_request,
                server="pre_ckan",
                user_info={"user": "test"}
            )

        assert exc_info.value.status_code == 400
        assert "disabled" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("api.routes.register_routes.post_service.add_service")
    @patch("api.routes.register_routes.post_service.catalog_settings")
    @patch("api.routes.register_routes.post_service.ckan_settings")
    async def test_create_service_pre_ckan_enabled(
        self, mock_ckan_settings, mock_catalog_settings, mock_add_service, mock_service_request
    ):
        """Test create service with pre_ckan enabled."""
        from api.routes.register_routes.post_service import create_service

        mock_ckan_settings.pre_ckan_enabled = True
        mock_repo = MagicMock()
        mock_repo.ckan = MagicMock()
        mock_catalog_settings.pre_catalog = mock_repo
        mock_add_service.return_value = "service-456"

        result = await create_service(
            data=mock_service_request,
            server="pre_ckan",
            user_info={"user": "test"}
        )

        assert result["id"] == "service-456"

    @pytest.mark.asyncio
    @patch("api.routes.register_routes.post_service.add_service")
    @patch("api.routes.register_routes.post_service.catalog_settings")
    @patch("api.routes.register_routes.post_service.ckan_settings")
    async def test_create_service_value_error(
        self, mock_ckan_settings, mock_catalog_settings, mock_add_service, mock_service_request
    ):
        """Test create service with ValueError."""
        from api.routes.register_routes.post_service import create_service
        from api.repositories import CKANRepository

        mock_repo = MagicMock(spec=CKANRepository)
        mock_repo.ckan = MagicMock()
        mock_catalog_settings.local_catalog = mock_repo
        mock_add_service.side_effect = ValueError("Invalid owner_org")

        with pytest.raises(HTTPException) as exc_info:
            await create_service(
                data=mock_service_request,
                server="local",
                user_info={"user": "test"}
            )

        assert exc_info.value.status_code == 400
        assert "Invalid owner_org" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.routes.register_routes.post_service.add_service")
    @patch("api.routes.register_routes.post_service.catalog_settings")
    @patch("api.routes.register_routes.post_service.ckan_settings")
    async def test_create_service_key_error(
        self, mock_ckan_settings, mock_catalog_settings, mock_add_service, mock_service_request
    ):
        """Test create service with KeyError."""
        from api.routes.register_routes.post_service import create_service
        from api.repositories import CKANRepository

        mock_repo = MagicMock(spec=CKANRepository)
        mock_repo.ckan = MagicMock()
        mock_catalog_settings.local_catalog = mock_repo
        mock_add_service.side_effect = KeyError("reserved_key")

        with pytest.raises(HTTPException) as exc_info:
            await create_service(
                data=mock_service_request,
                server="local",
                user_info={"user": "test"}
            )

        assert exc_info.value.status_code == 400
        assert "Reserved key error" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.routes.register_routes.post_service.add_service")
    @patch("api.routes.register_routes.post_service.catalog_settings")
    @patch("api.routes.register_routes.post_service.ckan_settings")
    async def test_create_service_duplicate_url(
        self, mock_ckan_settings, mock_catalog_settings, mock_add_service, mock_service_request
    ):
        """Test create service with duplicate URL."""
        from api.routes.register_routes.post_service import create_service
        from api.repositories import CKANRepository

        mock_repo = MagicMock(spec=CKANRepository)
        mock_repo.ckan = MagicMock()
        mock_catalog_settings.local_catalog = mock_repo
        mock_add_service.side_effect = Exception("That URL is already in use")

        with pytest.raises(HTTPException) as exc_info:
            await create_service(
                data=mock_service_request,
                server="local",
                user_info={"user": "test"}
            )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["error"] == "Duplicate Service"

    @pytest.mark.asyncio
    @patch("api.routes.register_routes.post_service.add_service")
    @patch("api.routes.register_routes.post_service.catalog_settings")
    @patch("api.routes.register_routes.post_service.ckan_settings")
    async def test_create_service_duplicate_name(
        self, mock_ckan_settings, mock_catalog_settings, mock_add_service, mock_service_request
    ):
        """Test create service with duplicate name."""
        from api.routes.register_routes.post_service import create_service
        from api.repositories import CKANRepository

        mock_repo = MagicMock(spec=CKANRepository)
        mock_repo.ckan = MagicMock()
        mock_catalog_settings.local_catalog = mock_repo
        mock_add_service.side_effect = Exception("That name is already in use")

        with pytest.raises(HTTPException) as exc_info:
            await create_service(
                data=mock_service_request,
                server="local",
                user_info={"user": "test"}
            )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    @patch("api.routes.register_routes.post_service.add_service")
    @patch("api.routes.register_routes.post_service.catalog_settings")
    @patch("api.routes.register_routes.post_service.ckan_settings")
    async def test_create_service_no_scheme(
        self, mock_ckan_settings, mock_catalog_settings, mock_add_service, mock_service_request
    ):
        """Test create service with No scheme supplied error."""
        from api.routes.register_routes.post_service import create_service
        from api.repositories import CKANRepository

        mock_repo = MagicMock(spec=CKANRepository)
        mock_repo.ckan = MagicMock()
        mock_catalog_settings.local_catalog = mock_repo
        mock_add_service.side_effect = Exception("No scheme supplied")

        with pytest.raises(HTTPException) as exc_info:
            await create_service(
                data=mock_service_request,
                server="local",
                user_info={"user": "test"}
            )

        assert exc_info.value.status_code == 400
        assert "not configured" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("api.routes.register_routes.post_service.add_service")
    @patch("api.routes.register_routes.post_service.catalog_settings")
    @patch("api.routes.register_routes.post_service.ckan_settings")
    async def test_create_service_generic_error(
        self, mock_ckan_settings, mock_catalog_settings, mock_add_service, mock_service_request
    ):
        """Test create service with generic error."""
        from api.routes.register_routes.post_service import create_service
        from api.repositories import CKANRepository

        mock_repo = MagicMock(spec=CKANRepository)
        mock_repo.ckan = MagicMock()
        mock_catalog_settings.local_catalog = mock_repo
        mock_add_service.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await create_service(
                data=mock_service_request,
                server="local",
                user_info={"user": "test"}
            )

        assert exc_info.value.status_code == 400
        assert "Error creating service" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.routes.register_routes.post_service.add_service")
    @patch("api.routes.register_routes.post_service.catalog_settings")
    @patch("api.routes.register_routes.post_service.ckan_settings")
    async def test_create_service_non_ckan_repository(
        self, mock_ckan_settings, mock_catalog_settings, mock_add_service, mock_service_request
    ):
        """Test create service with non-CKAN repository (MongoDB)."""
        from api.routes.register_routes.post_service import create_service

        mock_repo = MagicMock()  # Not a CKANRepository
        mock_catalog_settings.local_catalog = mock_repo
        mock_add_service.return_value = "service-789"

        result = await create_service(
            data=mock_service_request,
            server="local",
            user_info={"user": "test"}
        )

        assert result["id"] == "service-789"
        # ckan_instance should be None for non-CKAN repository
        call_args = mock_add_service.call_args
        assert call_args[1]["ckan_instance"] is None
