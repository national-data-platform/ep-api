# api/repositories/ckan_repository.py
"""
CKAN implementation of the DataCatalogRepository interface.

This module wraps the CKAN API client to conform to the repository
interface, allowing seamless integration with the existing CKAN infrastructure.
"""

from typing import Any, Dict, List

from api.repositories.base_repository import DataCatalogRepository


class CKANRepository(DataCatalogRepository):
    """
    CKAN implementation of the catalog repository.

    This class wraps a CKAN RemoteCKAN instance and delegates all
    operations to it while conforming to the DataCatalogRepository interface.

    Parameters
    ----------
    ckan_instance : RemoteCKAN
        An instance of ckanapi.RemoteCKAN configured with URL and API key
    """

    def __init__(self, ckan_instance):
        """
        Initialize the CKAN repository wrapper.

        Parameters
        ----------
        ckan_instance : RemoteCKAN
            Configured CKAN API client
        """
        self.ckan = ckan_instance

    def package_create(self, **kwargs) -> Dict[str, Any]:
        """
        Create a new package in CKAN.

        Delegates directly to CKAN's package_create action.

        Parameters
        ----------
        **kwargs
            Package creation parameters (name, title, owner_org, etc.)

        Returns
        -------
        dict
            Created package data from CKAN

        Raises
        ------
        Exception
            If CKAN package creation fails
        """
        return self.ckan.action.package_create(**kwargs)

    def package_show(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a package from CKAN.

        Parameters
        ----------
        id : str
            Package ID or name

        Returns
        -------
        dict
            Package data from CKAN

        Raises
        ------
        Exception
            If package not found in CKAN
        """
        return self.ckan.action.package_show(id=id)

    def package_update(self, **kwargs) -> Dict[str, Any]:
        """
        Update a package in CKAN.

        Parameters
        ----------
        **kwargs
            Package update parameters including 'id'

        Returns
        -------
        dict
            Updated package data from CKAN

        Raises
        ------
        Exception
            If CKAN package update fails
        """
        return self.ckan.action.package_update(**kwargs)

    def package_patch(self, **kwargs) -> Dict[str, Any]:
        """
        Partially update a package in CKAN.

        Parameters
        ----------
        **kwargs
            Package patch parameters including 'id'

        Returns
        -------
        dict
            Updated package data from CKAN

        Raises
        ------
        Exception
            If CKAN package patch fails
        """
        return self.ckan.action.package_patch(**kwargs)

    def package_delete(self, id: str) -> None:
        """
        Delete a package from CKAN.

        Parameters
        ----------
        id : str
            Package ID to delete

        Raises
        ------
        Exception
            If CKAN package deletion fails
        """
        self.ckan.action.package_delete(id=id)

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
        Search packages in CKAN.

        Parameters
        ----------
        q : str
            Search query
        fq : str
            Filter query
        rows : int
            Number of results
        start : int
            Offset for pagination
        sort : str
            Sort order
        **kwargs
            Additional search parameters

        Returns
        -------
        dict
            Search results with 'count' and 'results' keys

        Raises
        ------
        Exception
            If CKAN search fails
        """
        return self.ckan.action.package_search(
            q=q, fq=fq, rows=rows, start=start, sort=sort, **kwargs
        )

    def resource_create(self, **kwargs) -> Dict[str, Any]:
        """
        Create a resource in CKAN.

        Parameters
        ----------
        **kwargs
            Resource creation parameters (package_id, name, url, etc.)

        Returns
        -------
        dict
            Created resource data from CKAN

        Raises
        ------
        Exception
            If CKAN resource creation fails
        """
        return self.ckan.action.resource_create(**kwargs)

    def resource_show(self, id: str) -> Dict[str, Any]:
        """
        Retrieve a resource from CKAN.

        Parameters
        ----------
        id : str
            Resource ID

        Returns
        -------
        dict
            Resource data from CKAN

        Raises
        ------
        Exception
            If resource not found in CKAN
        """
        return self.ckan.action.resource_show(id=id)

    def resource_delete(self, id: str) -> None:
        """
        Delete a resource from CKAN.

        Parameters
        ----------
        id : str
            Resource ID to delete

        Raises
        ------
        Exception
            If CKAN resource deletion fails
        """
        self.ckan.action.resource_delete(id=id)

    def organization_create(self, **kwargs) -> Dict[str, Any]:
        """
        Create an organization in CKAN.

        Parameters
        ----------
        **kwargs
            Organization creation parameters (name, title, etc.)

        Returns
        -------
        dict
            Created organization data from CKAN

        Raises
        ------
        Exception
            If CKAN organization creation fails
        """
        return self.ckan.action.organization_create(**kwargs)

    def organization_show(self, id: str) -> Dict[str, Any]:
        """
        Retrieve an organization from CKAN.

        Parameters
        ----------
        id : str
            Organization ID or name

        Returns
        -------
        dict
            Organization data from CKAN

        Raises
        ------
        Exception
            If organization not found in CKAN
        """
        return self.ckan.action.organization_show(id=id)

    def organization_list(
        self, all_fields: bool = False, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        List organizations from CKAN.

        Parameters
        ----------
        all_fields : bool
            If True, return full data; if False, return only names
        **kwargs
            Additional parameters

        Returns
        -------
        list
            List of organizations from CKAN
        """
        return self.ckan.action.organization_list(all_fields=all_fields, **kwargs)

    def organization_delete(self, id: str) -> None:
        """
        Delete an organization from CKAN.

        Parameters
        ----------
        id : str
            Organization ID to delete

        Raises
        ------
        Exception
            If CKAN organization deletion fails
        """
        self.ckan.action.organization_delete(id=id)
