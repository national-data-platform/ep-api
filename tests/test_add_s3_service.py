# tests/test_add_s3_service.py

from unittest.mock import MagicMock, patch

import pytest

from api.services.s3_services.add_s3 import RESERVED_KEYS, add_s3


class TestAddS3Service:
    """Test cases for the add_s3 service function."""

    def test_add_s3_success_minimal_params(self):
        """Test successful S3 resource creation with minimal parameters."""
        with patch(
            "api.services.s3_services.add_s3.catalog_settings"
        ) as mock_catalog_settings:
            # Mock repository
            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            # Mock successful package creation
            mock_package = {"id": "test-package-id-123"}
            mock_repo.package_create.return_value = mock_package

            # Mock successful resource creation
            mock_repo.resource_create.return_value = {"id": "test-resource-id-123"}

            result = add_s3(
                resource_name="test_s3_resource",
                resource_title="Test S3 Resource",
                owner_org="test_org",
                resource_s3="s3://test-bucket/test-file.csv",
            )

            assert result == "test-package-id-123"

            # Verify package creation was called with correct parameters
            mock_repo.package_create.assert_called_once_with(
                name="test_s3_resource",
                title="Test S3 Resource",
                owner_org="test_org",
                notes="",
            )

            # Verify resource creation was called with correct parameters
            mock_repo.resource_create.assert_called_once_with(
                package_id="test-package-id-123",
                url="s3://test-bucket/test-file.csv",
                name="test_s3_resource",
                description="Resource pointing to s3://test-bucket/test-file.csv",
                format="s3",
            )

    def test_add_s3_success_with_all_params(self):
        """Test successful S3 resource creation with all parameters."""
        with (
            patch(
                "api.services.s3_services.add_s3.catalog_settings"
            ) as mock_catalog_settings,
            patch("api.services.s3_services.add_s3.inject_ndp_metadata") as mock_inject,
        ):

            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            mock_package = {"id": "test-package-id-456"}
            mock_repo.package_create.return_value = mock_package
            mock_repo.resource_create.return_value = {"id": "test-resource-id-456"}

            # Mock NDP metadata injection
            original_extras = {"custom_field": "custom_value"}
            injected_extras = {"custom_field": "custom_value", "ndp_user": "test_user"}
            mock_inject.return_value = injected_extras

            user_info = {"user": "test_user", "org": "test_org"}

            result = add_s3(
                resource_name="full_s3_resource",
                resource_title="Full S3 Resource",
                owner_org="test_org_full",
                resource_s3="s3://full-bucket/full-file.json",
                notes="This is a full test S3 resource",
                extras=original_extras,
                user_info=user_info,
            )

            assert result == "test-package-id-456"

            # Verify NDP metadata injection was called
            mock_inject.assert_called_once_with(user_info, original_extras)

            # Verify package creation with injected extras
            expected_package_dict = {
                "name": "full_s3_resource",
                "title": "Full S3 Resource",
                "owner_org": "test_org_full",
                "notes": "This is a full test S3 resource",
                "extras": [
                    {"key": "custom_field", "value": "custom_value"},
                    {"key": "ndp_user", "value": "test_user"},
                ],
            }
            mock_repo.package_create.assert_called_once_with(**expected_package_dict)

    def test_add_s3_success_with_custom_ckan_instance(self):
        """Test successful S3 resource creation with custom CKAN instance."""
        # Create custom CKAN instance
        custom_ckan = MagicMock()
        mock_package = {"id": "custom-package-id"}
        custom_ckan.action.package_create.return_value = mock_package
        custom_ckan.action.resource_create.return_value = {"id": "custom-resource-id"}

        result = add_s3(
            resource_name="custom_s3_resource",
            resource_title="Custom S3 Resource",
            owner_org="custom_org",
            resource_s3="s3://custom-bucket/custom-file.txt",
            ckan_instance=custom_ckan,
        )

        assert result == "custom-package-id"

        # Verify custom CKAN instance was used
        custom_ckan.action.package_create.assert_called_once()
        custom_ckan.action.resource_create.assert_called_once()

    def test_add_s3_success_with_empty_extras(self):
        """Test successful S3 resource creation with empty extras dict."""
        with patch(
            "api.services.s3_services.add_s3.catalog_settings"
        ) as mock_catalog_settings:
            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            mock_package = {"id": "empty-extras-id"}
            mock_repo.package_create.return_value = mock_package
            mock_repo.resource_create.return_value = {"id": "empty-resource-id"}

            result = add_s3(
                resource_name="empty_extras_s3",
                resource_title="Empty Extras S3",
                owner_org="test_org",
                resource_s3="s3://bucket/file.csv",
                extras={},
            )

            assert result == "empty-extras-id"

            # Should not include extras in package creation when empty
            mock_repo.package_create.assert_called_once_with(
                name="empty_extras_s3",
                title="Empty Extras S3",
                owner_org="test_org",
                notes="",
            )

    def test_add_s3_success_with_none_extras(self):
        """Test successful S3 resource creation with None extras."""
        with patch(
            "api.services.s3_services.add_s3.catalog_settings"
        ) as mock_catalog_settings:
            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            mock_package = {"id": "none-extras-id"}
            mock_repo.package_create.return_value = mock_package
            mock_repo.resource_create.return_value = {"id": "none-resource-id"}

            result = add_s3(
                resource_name="none_extras_s3",
                resource_title="None Extras S3",
                owner_org="test_org",
                resource_s3="s3://bucket/file.csv",
                extras=None,
            )

            assert result == "none-extras-id"

    def test_add_s3_invalid_extras_type_string(self):
        """Test validation error when extras is a string."""
        with pytest.raises(ValueError, match="Extras must be a dictionary or None."):
            add_s3(
                resource_name="test_s3",
                resource_title="Test S3",
                owner_org="test_org",
                resource_s3="s3://bucket/file.csv",
                extras="invalid_extras",
            )

    def test_add_s3_invalid_extras_type_list(self):
        """Test validation error when extras is a list."""
        with pytest.raises(ValueError, match="Extras must be a dictionary or None."):
            add_s3(
                resource_name="test_s3",
                resource_title="Test S3",
                owner_org="test_org",
                resource_s3="s3://bucket/file.csv",
                extras=["invalid", "extras"],
            )

    def test_add_s3_invalid_extras_type_integer(self):
        """Test validation error when extras is an integer."""
        with pytest.raises(ValueError, match="Extras must be a dictionary or None."):
            add_s3(
                resource_name="test_s3",
                resource_title="Test S3",
                owner_org="test_org",
                resource_s3="s3://bucket/file.csv",
                extras=123,
            )

    def test_add_s3_reserved_keys_error_single(self):
        """Test KeyError when extras contains a single reserved key."""
        reserved_extras = {"name": "reserved_name", "custom_field": "valid_value"}

        with pytest.raises(KeyError, match="Extras contain reserved keys:"):
            add_s3(
                resource_name="test_s3",
                resource_title="Test S3",
                owner_org="test_org",
                resource_s3="s3://bucket/file.csv",
                extras=reserved_extras,
            )

    def test_add_s3_reserved_keys_error_multiple(self):
        """Test KeyError when extras contains multiple reserved keys."""
        reserved_extras = {
            "name": "reserved_name",
            "title": "reserved_title",
            "owner_org": "reserved_org",
            "custom_field": "valid_value",
        }

        with pytest.raises(KeyError, match="Extras contain reserved keys:"):
            add_s3(
                resource_name="test_s3",
                resource_title="Test S3",
                owner_org="test_org",
                resource_s3="s3://bucket/file.csv",
                extras=reserved_extras,
            )

    def test_add_s3_package_creation_error(self):
        """Test exception handling when package creation fails."""
        with patch(
            "api.services.s3_services.add_s3.catalog_settings"
        ) as mock_catalog_settings:
            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            # Mock package creation failure
            mock_repo.package_create.side_effect = Exception(
                "CKAN package creation error"
            )

            with pytest.raises(
                Exception,
                match="Error creating resource package: CKAN package creation error",
            ):
                add_s3(
                    resource_name="test_s3",
                    resource_title="Test S3",
                    owner_org="test_org",
                    resource_s3="s3://bucket/file.csv",
                )

    def test_add_s3_resource_creation_error(self):
        """Test exception handling when resource creation fails."""
        with patch(
            "api.services.s3_services.add_s3.catalog_settings"
        ) as mock_catalog_settings:
            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            # Mock successful package creation
            mock_package = {"id": "test-package-error"}
            mock_repo.package_create.return_value = mock_package

            # Mock resource creation failure
            mock_repo.resource_create.side_effect = Exception(
                "S3 resource creation failed"
            )

            with pytest.raises(
                Exception, match="Error creating resource: S3 resource creation failed"
            ):
                add_s3(
                    resource_name="test_s3",
                    resource_title="Test S3",
                    owner_org="test_org",
                    resource_s3="s3://bucket/file.csv",
                )

    def test_add_s3_package_without_id(self):
        """Test handling when package creation returns without ID (edge case)."""
        with patch(
            "api.services.s3_services.add_s3.catalog_settings"
        ) as mock_catalog_settings:
            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            # Mock package creation returning dict without 'id' field
            mock_package = {"name": "test_package"}  # No 'id' field
            mock_repo.package_create.return_value = mock_package

            with pytest.raises(
                Exception, match="Error creating resource package: 'id'"
            ):
                add_s3(
                    resource_name="test_s3",
                    resource_title="Test S3",
                    owner_org="test_org",
                    resource_s3="s3://bucket/file.csv",
                )

    def test_add_s3_package_with_none_id(self):
        """Test handling when package creation returns None ID."""
        with patch(
            "api.services.s3_services.add_s3.catalog_settings"
        ) as mock_catalog_settings:
            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            # Mock package creation returning None ID
            mock_package = {"id": None}
            mock_repo.package_create.return_value = mock_package

            with pytest.raises(Exception, match="Unknown error occurred"):
                add_s3(
                    resource_name="test_s3",
                    resource_title="Test S3",
                    owner_org="test_org",
                    resource_s3="s3://bucket/file.csv",
                )

    def test_add_s3_package_with_empty_string_id(self):
        """Test handling when package creation returns empty string ID."""
        with patch(
            "api.services.s3_services.add_s3.catalog_settings"
        ) as mock_catalog_settings:
            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            # Mock package creation returning empty string ID
            mock_package = {"id": ""}
            mock_repo.package_create.return_value = mock_package

            with pytest.raises(Exception, match="Unknown error occurred"):
                add_s3(
                    resource_name="test_s3",
                    resource_title="Test S3",
                    owner_org="test_org",
                    resource_s3="s3://bucket/file.csv",
                )

    def test_add_s3_with_user_info_but_no_extras(self):
        """Test S3 creation with user_info but no extras (NDP metadata injection)."""
        with (
            patch(
                "api.services.s3_services.add_s3.catalog_settings"
            ) as mock_catalog_settings,
            patch("api.services.s3_services.add_s3.inject_ndp_metadata") as mock_inject,
        ):

            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            mock_package = {"id": "ndp-metadata-id"}
            mock_repo.package_create.return_value = mock_package
            mock_repo.resource_create.return_value = {"id": "ndp-resource-id"}

            # Mock NDP metadata injection
            injected_extras = {"ndp_user": "test_user", "ndp_org": "test_org"}
            mock_inject.return_value = injected_extras

            user_info = {"user": "test_user", "org": "test_org"}

            result = add_s3(
                resource_name="ndp_s3",
                resource_title="NDP S3",
                owner_org="test_org",
                resource_s3="s3://bucket/file.csv",
                user_info=user_info,
            )

            assert result == "ndp-metadata-id"

            # Verify NDP metadata injection was called with empty dict
            mock_inject.assert_called_once_with(user_info, {})

    def test_reserved_keys_constant(self):
        """Test that RESERVED_KEYS contains expected values."""
        expected_keys = {
            "name",
            "title",
            "owner_org",
            "notes",
            "id",
            "resources",
            "collection",
        }
        assert RESERVED_KEYS == expected_keys

    def test_add_s3_extras_copy_isolation(self):
        """Test that original extras dict is not modified during processing."""
        with (
            patch(
                "api.services.s3_services.add_s3.catalog_settings"
            ) as mock_catalog_settings,
            patch("api.services.s3_services.add_s3.inject_ndp_metadata") as mock_inject,
        ):

            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            mock_package = {"id": "copy-test-id"}
            mock_repo.package_create.return_value = mock_package
            mock_repo.resource_create.return_value = {"id": "copy-resource-id"}

            # Original extras
            original_extras = {"custom_field": "original_value"}

            # Mock injection to return modified extras
            injected_extras = {
                "custom_field": "original_value",
                "ndp_injected": "injected_value",
            }
            mock_inject.return_value = injected_extras

            user_info = {"user": "test_user"}

            add_s3(
                resource_name="copy_test_s3",
                resource_title="Copy Test S3",
                owner_org="test_org",
                resource_s3="s3://bucket/file.csv",
                extras=original_extras,
                user_info=user_info,
            )

            # Verify original extras dict was not modified
            assert original_extras == {"custom_field": "original_value"}
            assert "ndp_injected" not in original_extras

    def test_add_s3_success_with_various_s3_urls(self):
        """Test successful S3 resource creation with different S3 URL formats."""
        with patch(
            "api.services.s3_services.add_s3.catalog_settings"
        ) as mock_catalog_settings:
            mock_repo = MagicMock()
            mock_catalog_settings.local_catalog = mock_repo

            mock_package = {"id": "url-format-test-id"}
            mock_repo.package_create.return_value = mock_package
            mock_repo.resource_create.return_value = {"id": "url-format-resource-id"}

            s3_urls = [
                "s3://bucket/file.csv",
                "s3://my-bucket/folder/subfolder/data.json",
                "s3://bucket-with-dashes/file_with_underscores.txt",
                "s3://bucket123/folder123/file123.xlsx",
            ]

            for s3_url in s3_urls:
                result = add_s3(
                    resource_name=f"test_s3_{s3_url.split('/')[-1]}",
                    resource_title=f"Test S3 {s3_url.split('/')[-1]}",
                    owner_org="test_org",
                    resource_s3=s3_url,
                )

                assert result == "url-format-test-id"

                # Verify resource was created with correct S3 URL
                last_call = mock_repo.resource_create.call_args
                assert last_call[1]["url"] == s3_url
                assert last_call[1]["description"] == f"Resource pointing to {s3_url}"

                # Reset mock for next iteration
                mock_repo.reset_mock()
                mock_repo.package_create.return_value = mock_package
                mock_repo.resource_create.return_value = {
                    "id": "url-format-resource-id"
                }
