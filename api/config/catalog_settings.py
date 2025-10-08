# api/config/catalog_settings.py
"""
Catalog backend configuration and repository factory.

This module provides centralized configuration for the catalog backend,
allowing seamless switching between CKAN and MongoDB (or other implementations)
through environment variables.
"""

from pydantic_settings import BaseSettings

from api.config.ckan_settings import ckan_settings
from api.repositories.base_repository import DataCatalogRepository
from api.repositories.ckan_repository import CKANRepository
from api.repositories.mongodb_repository import MongoDBRepository


class CatalogSettings(BaseSettings):
    """
    Configuration settings for catalog backend selection.

    Attributes
    ----------
    local_catalog_backend : str
        Backend type for local catalog: "ckan" or "mongodb" (default: "ckan")
    mongodb_connection_string : str
        MongoDB connection URI (default: "mongodb://localhost:27017")
    mongodb_database : str
        MongoDB database name for local catalog (default: "ndp_local_catalog")
    """

    # Backend selection for LOCAL catalog only
    # Global and PreCKAN always use CKAN
    local_catalog_backend: str = "ckan"

    # MongoDB configuration (only used if local_catalog_backend="mongodb")
    mongodb_connection_string: str = "mongodb://localhost:27017"
    mongodb_database: str = "ndp_local_catalog"

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }

    @property
    def local_catalog(self) -> DataCatalogRepository:
        """
        Get the repository for the local catalog.

        Returns a repository instance based on the LOCAL_CATALOG_BACKEND
        environment variable. Can be CKAN or MongoDB.

        Returns
        -------
        DataCatalogRepository
            Configured repository for local catalog operations

        Raises
        ------
        ValueError
            If an unsupported backend type is specified
        """
        backend = self.local_catalog_backend.lower()

        if backend == "mongodb":
            return MongoDBRepository(
                connection_string=self.mongodb_connection_string,
                database_name=self.mongodb_database,
            )
        elif backend == "ckan":
            return CKANRepository(ckan_settings.ckan)
        else:
            raise ValueError(
                f"Unsupported catalog backend: {backend}. "
                f"Supported backends: 'ckan', 'mongodb'"
            )

    @property
    def global_catalog(self) -> DataCatalogRepository:
        """
        Get the repository for the global NDP catalog.

        This always returns a CKAN repository pointing to the global
        NDP catalog, regardless of local_catalog_backend setting.

        Returns
        -------
        DataCatalogRepository
            CKAN repository for global catalog (read-only)
        """
        return CKANRepository(ckan_settings.ckan_global)

    @property
    def pre_catalog(self) -> DataCatalogRepository:
        """
        Get the repository for the PreCKAN staging catalog.

        This always returns a CKAN repository pointing to the PreCKAN
        staging environment, regardless of local_catalog_backend setting.

        Returns
        -------
        DataCatalogRepository
            CKAN repository for PreCKAN catalog
        """
        return CKANRepository(ckan_settings.pre_ckan)

    def get_repository_by_name(self, catalog_name: str) -> DataCatalogRepository:
        """
        Get a repository by catalog name.

        This is a convenience method for accessing different catalogs
        by name string.

        Parameters
        ----------
        catalog_name : str
            One of: "local", "global", "pre"

        Returns
        -------
        DataCatalogRepository
            The requested catalog repository

        Raises
        ------
        ValueError
            If catalog_name is not recognized
        """
        if catalog_name == "local":
            return self.local_catalog
        elif catalog_name == "global":
            return self.global_catalog
        elif catalog_name == "pre":
            return self.pre_catalog
        else:
            raise ValueError(
                f"Unknown catalog name: {catalog_name}. "
                f"Valid options: 'local', 'global', 'pre'"
            )


# Global instance
catalog_settings = CatalogSettings()
