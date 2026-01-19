# tests/repositories/test_catalog_settings.py
"""
Tests for catalog settings and repository factory pattern.
"""

import pytest
from unittest.mock import patch, MagicMock
from api.config.catalog_settings import CatalogSettings
from api.repositories import CKANRepository, MongoDBRepository


def test_catalog_settings_default_backend():
    """Test that default backend is read from environment or defaults to ckan."""
    settings = CatalogSettings()
    # Should be either 'ckan' or 'mongodb' depending on env configuration
    assert settings.local_catalog_backend in ["ckan", "mongodb"]


def test_catalog_settings_local_catalog_ckan():
    """Test getting CKAN repository for local catalog."""
    with patch.dict("os.environ", {"LOCAL_CATALOG_BACKEND": "ckan"}):
        settings = CatalogSettings()
        repo = settings.local_catalog
        assert isinstance(repo, CKANRepository)


def test_catalog_settings_local_catalog_mongodb():
    """Test getting MongoDB repository for local catalog."""
    with patch.dict(
        "os.environ",
        {
            "LOCAL_CATALOG_BACKEND": "mongodb",
            "MONGODB_CONNECTION_STRING": "mongodb://localhost:27017",
            "MONGODB_DATABASE": "test_db",
        },
    ):
        # Mock MongoClient to avoid actual MongoDB connection
        with patch("api.repositories.mongodb_repository.MongoClient") as mock_client:
            mock_client.return_value = MagicMock()
            settings = CatalogSettings()
            repo = settings.local_catalog
            assert isinstance(repo, MongoDBRepository)


def test_catalog_settings_unsupported_backend():
    """Test that unsupported backend raises ValueError."""
    with patch.dict("os.environ", {"LOCAL_CATALOG_BACKEND": "unsupported"}):
        settings = CatalogSettings()
        with pytest.raises(ValueError, match="Unsupported catalog backend"):
            _ = settings.local_catalog


def test_catalog_settings_global_catalog():
    """Test that global catalog always returns CKAN repository."""
    settings = CatalogSettings()
    repo = settings.global_catalog
    assert isinstance(repo, CKANRepository)


def test_catalog_settings_pre_catalog():
    """Test that pre catalog always returns CKAN repository."""
    settings = CatalogSettings()
    repo = settings.pre_catalog
    assert isinstance(repo, CKANRepository)


def test_get_repository_by_name_local():
    """Test getting local repository by name."""
    # Mock MongoDB client if backend is mongodb
    with patch("api.repositories.mongodb_repository.MongoClient") as mock_client:
        mock_client.return_value = MagicMock()
        settings = CatalogSettings()
        repo = settings.get_repository_by_name("local")
        assert repo is not None


def test_get_repository_by_name_global():
    """Test getting global repository by name."""
    settings = CatalogSettings()
    repo = settings.get_repository_by_name("global")
    assert isinstance(repo, CKANRepository)


def test_get_repository_by_name_pre():
    """Test getting pre repository by name."""
    settings = CatalogSettings()
    repo = settings.get_repository_by_name("pre")
    assert isinstance(repo, CKANRepository)


def test_get_repository_by_name_invalid():
    """Test that invalid repository name raises ValueError."""
    settings = CatalogSettings()
    with pytest.raises(ValueError, match="Unknown catalog name"):
        settings.get_repository_by_name("invalid")


def test_mongodb_settings_custom_values():
    """Test custom MongoDB connection settings."""
    custom_connection = "mongodb://custom-host:27017"
    custom_db = "custom_database"

    with patch.dict(
        "os.environ",
        {
            "LOCAL_CATALOG_BACKEND": "mongodb",
            "MONGODB_CONNECTION_STRING": custom_connection,
            "MONGODB_DATABASE": custom_db,
        },
    ):
        # Mock MongoClient to avoid actual MongoDB connection
        with patch("api.repositories.mongodb_repository.MongoClient") as mock_client:
            mock_client.return_value = MagicMock()
            settings = CatalogSettings()
            assert settings.mongodb_connection_string == custom_connection
            assert settings.mongodb_database == custom_db

            repo = settings.local_catalog
            assert isinstance(repo, MongoDBRepository)
