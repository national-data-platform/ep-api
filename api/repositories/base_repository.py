# api/repositories/base_repository.py
"""
Abstract base class for data catalog repositories.

This module defines the interface that all catalog backend implementations
must follow to ensure compatibility across different storage systems.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DataCatalogRepository(ABC):
    """
    Abstract base class for data catalog operations.

    This interface defines all the operations that a data catalog backend
    must support. Implementations can use different underlying technologies
    (CKAN, MongoDB, PostgreSQL, Elasticsearch, etc.) as long as they
    conform to this interface.

    The return types and structures should match CKAN's API responses
    to ensure compatibility with existing code.
    """

    @abstractmethod
    def package_create(self, **kwargs) -> Dict[str, Any]:
        """
        Create a new dataset/package in the catalog.

        Parameters
        ----------
        name : str
            Unique identifier for the package
        title : str
            Human-readable title
        owner_org : str
            Organization ID that owns this package
        notes : str, optional
            Description/notes about the package
        extras : list, optional
            List of dicts with 'key' and 'value' for additional metadata

        Returns
        -------
        dict
            Created package data including 'id', 'name', 'title', etc.

        Raises
        ------
        Exception
            If package creation fails
        """
        pass

    @abstractmethod
    def package_show(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a package by its ID or name.

        Parameters
        ----------
        id : str
            Package ID or name

        Returns
        -------
        dict
            Package data including all fields and resources

        Raises
        ------
        Exception
            If package not found or retrieval fails
        """
        pass

    @abstractmethod
    def package_update(self, **kwargs) -> Dict[str, Any]:
        """
        Update an existing package.

        Parameters
        ----------
        id : str
            Package ID to update
        **kwargs
            Fields to update (name, title, notes, extras, etc.)

        Returns
        -------
        dict
            Updated package data

        Raises
        ------
        Exception
            If package not found or update fails
        """
        pass

    @abstractmethod
    def package_patch(self, **kwargs) -> Dict[str, Any]:
        """
        Partially update a package (only specified fields).

        Parameters
        ----------
        id : str
            Package ID to patch
        **kwargs
            Fields to update

        Returns
        -------
        dict
            Updated package data

        Raises
        ------
        Exception
            If package not found or patch fails
        """
        pass

    @abstractmethod
    def package_delete(self, id: str) -> None:
        """
        Delete a package.

        Parameters
        ----------
        id : str
            Package ID to delete

        Raises
        ------
        Exception
            If package not found or deletion fails
        """
        pass

    @abstractmethod
    def package_search(
        self,
        q: str = "*:*",
        fq: str = "",
        rows: int = 10,
        start: int = 0,
        sort: str = "score desc, metadata_modified desc",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search for packages matching a query.

        Parameters
        ----------
        q : str
            Search query (default "*:*" for all)
        fq : str
            Filter query
        rows : int
            Number of results to return
        start : int
            Offset for pagination
        sort : str
            Sort order

        Returns
        -------
        dict
            Search results with 'count' and 'results' keys
        """
        pass

    @abstractmethod
    def resource_create(self, **kwargs) -> Dict[str, Any]:
        """
        Create a new resource within a package.

        Parameters
        ----------
        package_id : str
            Package ID to add resource to
        name : str
            Resource name
        url : str
            Resource URL (can be external or S3 path)
        description : str, optional
            Resource description
        format : str, optional
            Resource format (e.g., 'csv', 's3', 'url', 'kafka')

        Returns
        -------
        dict
            Created resource data including 'id'

        Raises
        ------
        Exception
            If resource creation fails
        """
        pass

    @abstractmethod
    def resource_show(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a resource by its ID.

        Parameters
        ----------
        id : str
            Resource ID

        Returns
        -------
        dict
            Resource data

        Raises
        ------
        Exception
            If resource not found
        """
        pass

    @abstractmethod
    def resource_delete(self, id: str) -> None:
        """
        Delete a resource.

        Parameters
        ----------
        id : str
            Resource ID to delete

        Raises
        ------
        Exception
            If resource not found or deletion fails
        """
        pass

    @abstractmethod
    def organization_create(self, **kwargs) -> Dict[str, Any]:
        """
        Create a new organization.

        Parameters
        ----------
        name : str
            Unique organization name
        title : str, optional
            Human-readable title
        description : str, optional
            Organization description

        Returns
        -------
        dict
            Created organization data

        Raises
        ------
        Exception
            If organization creation fails
        """
        pass

    @abstractmethod
    def organization_show(self, id: str) -> Dict[str, Any]:
        """
        Retrieve an organization by ID or name.

        Parameters
        ----------
        id : str
            Organization ID or name

        Returns
        -------
        dict
            Organization data

        Raises
        ------
        Exception
            If organization not found
        """
        pass

    @abstractmethod
    def organization_list(
        self, all_fields: bool = False, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        List all organizations.

        Parameters
        ----------
        all_fields : bool
            If True, return full organization data; if False, return only names

        Returns
        -------
        list
            List of organizations
        """
        pass

    @abstractmethod
    def organization_delete(self, id: str) -> None:
        """
        Delete an organization.

        Parameters
        ----------
        id : str
            Organization ID to delete

        Raises
        ------
        Exception
            If organization not found or deletion fails
        """
        pass

    @abstractmethod
    def check_health(self) -> bool:
        """
        Check if the catalog backend is reachable and operational.

        Returns
        -------
        bool
            True if backend is healthy and reachable, False otherwise
        """
        pass
