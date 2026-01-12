# tests/test_metadata_injection.py
"""
Tests for metadata injection service.
"""
import pytest
from unittest.mock import patch

from api.services.metadata_services.metadata_injection import (
    hash_user_id,
    inject_ndp_metadata,
)


class TestHashUserId:
    """Test cases for hash_user_id function."""

    def test_hash_user_id_with_sub(self):
        """Test hashing user ID when sub is present."""
        user_info = {"sub": "user123"}

        result = hash_user_id(user_info)

        assert isinstance(result, str)
        assert len(result) == 16
        # Hash should be deterministic
        assert result == hash_user_id(user_info)

    def test_hash_user_id_without_sub(self):
        """Test hashing when sub is missing (uses 'unknown')."""
        user_info = {}

        result = hash_user_id(user_info)

        assert isinstance(result, str)
        assert len(result) == 16
        # Should hash 'unknown'
        expected = hash_user_id({"sub": "unknown"})
        assert result == expected

    def test_hash_user_id_different_subs_produce_different_hashes(self):
        """Test that different sub values produce different hashes."""
        user1 = {"sub": "user1"}
        user2 = {"sub": "user2"}

        hash1 = hash_user_id(user1)
        hash2 = hash_user_id(user2)

        assert hash1 != hash2


class TestInjectNdpMetadata:
    """Test cases for inject_ndp_metadata function."""

    @patch("api.services.metadata_services.metadata_injection.swagger_settings")
    def test_inject_metadata_with_no_existing_extras(self, mock_settings):
        """Test injecting metadata when no extras exist."""
        mock_settings.organization = "test-org"

        user_info = {"sub": "user123"}

        result = inject_ndp_metadata(user_info)

        assert "ndp_group_id" in result
        assert result["ndp_group_id"] == "test-org"
        assert "ndp_user_id" in result
        assert len(result["ndp_user_id"]) == 16

    @patch("api.services.metadata_services.metadata_injection.swagger_settings")
    def test_inject_metadata_with_existing_extras(self, mock_settings):
        """Test injecting metadata with existing extras."""
        mock_settings.organization = "my-org"

        user_info = {"sub": "user456"}
        existing_extras = {"custom_field": "value", "version": "1.0"}

        result = inject_ndp_metadata(user_info, existing_extras)

        # Should preserve existing fields
        assert result["custom_field"] == "value"
        assert result["version"] == "1.0"
        # Should add NDP fields
        assert result["ndp_group_id"] == "my-org"
        assert "ndp_user_id" in result

    @patch("api.services.metadata_services.metadata_injection.swagger_settings")
    def test_inject_metadata_does_not_modify_original(self, mock_settings):
        """Test that original extras dict is not modified."""
        mock_settings.organization = "test-org"

        user_info = {"sub": "user789"}
        original_extras = {"key": "value"}

        result = inject_ndp_metadata(user_info, original_extras)

        # Original should be unchanged
        assert "ndp_group_id" not in original_extras
        assert "ndp_user_id" not in original_extras
        assert original_extras == {"key": "value"}
        # Result should have new fields
        assert "ndp_group_id" in result
        assert "key" in result

    @patch("api.services.metadata_services.metadata_injection.swagger_settings")
    def test_inject_metadata_overwrites_existing_ndp_fields(self, mock_settings):
        """Test that NDP fields are overwritten if they exist."""
        mock_settings.organization = "new-org"

        user_info = {"sub": "user999"}
        existing_extras = {
            "ndp_group_id": "old-org",
            "ndp_user_id": "old-hash",
            "other": "data",
        }

        result = inject_ndp_metadata(user_info, existing_extras)

        assert result["ndp_group_id"] == "new-org"
        assert result["ndp_user_id"] != "old-hash"
        assert result["other"] == "data"

    @patch("api.services.metadata_services.metadata_injection.swagger_settings")
    def test_inject_metadata_empty_extras_dict(self, mock_settings):
        """Test injecting metadata with empty extras dict."""
        mock_settings.organization = "empty-org"

        user_info = {"sub": "user000"}

        result = inject_ndp_metadata(user_info, {})

        assert "ndp_group_id" in result
        assert result["ndp_group_id"] == "empty-org"
        assert len(result) == 2  # Only NDP fields

    @patch("api.services.metadata_services.metadata_injection.swagger_settings")
    def test_inject_metadata_user_without_sub(self, mock_settings):
        """Test injecting metadata when user has no sub field."""
        mock_settings.organization = "test-org"

        user_info = {}

        result = inject_ndp_metadata(user_info)

        assert "ndp_user_id" in result
        # Should use 'unknown' hash
        expected_hash = hash_user_id({})
        assert result["ndp_user_id"] == expected_hash
