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
    def resource_patch(self, **kwargs) -> Dict[str, Any]:
        """
        Partially update a resource (only specified fields).

        Parameters
        ----------
        id : str
            Resource ID to patch
        **kwargs
            Fields to update (name, url, description, format, etc.)

        Returns
        -------
        dict
            Updated resource data

        Raises
        ------
        Exception
            If resource not found or patch fails
        """
        pass

    def resource_search(
        self,
        query: Optional[str] = None,
        name: Optional[str] = None,
        url: Optional[str] = None,
        format: Optional[str] = None,
        description: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Search for resources matching the given criteria.

        This is an optional method that backends can implement for
        resource-level searching. The default implementation searches
        through all packages and filters resources.

        Parameters
        ----------
        query : str, optional
            General search query (searches name, url, description)
        name : str, optional
            Filter by resource name (partial match)
        url : str, optional
            Filter by resource URL (partial match)
        format : str, optional
            Filter by resource format (exact match, case-insensitive)
        description : str, optional
            Filter by description (partial match)
        limit : int
            Maximum number of results to return
        offset : int
            Number of results to skip for pagination

        Returns
        -------
        dict
            Search results with 'count' and 'results' keys
        """
        # Default implementation - search through all packages
        all_packages = self.package_search(q="*:*", rows=1000)
        resources = []

        for package in all_packages.get("results", []):
            for resource in package.get("resources", []):
                # Apply filters
                if query:
                    query_lower = query.lower()
                    matches = (
                        query_lower in resource.get("name", "").lower()
                        or query_lower in resource.get("url", "").lower()
                        or query_lower in resource.get("description", "").lower()
                    )
                    if not matches:
                        continue

                if name and name.lower() not in resource.get("name", "").lower():
                    continue

                if url and url.lower() not in resource.get("url", "").lower():
                    continue

                if format and format.lower() != resource.get("format", "").lower():
                    continue

                if description and description.lower() not in resource.get(
                    "description", ""
                ).lower():
                    continue

                # Add package info to resource for context
                resource_with_context = resource.copy()
                resource_with_context["dataset_id"] = package.get("id")
                resource_with_context["dataset_name"] = package.get("name")
                resource_with_context["dataset_title"] = package.get("title")
                resources.append(resource_with_context)

        # Apply pagination
        total_count = len(resources)
        paginated = resources[offset : offset + limit]

        return {"count": total_count, "results": paginated}

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
