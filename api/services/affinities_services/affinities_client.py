# api/services/affinities_services/affinities_client.py
"""
HTTP client for NDP Affinities API.

This module provides an async client for registering datasets, services,
and their relationships with the Affinities system.
"""

import logging
from typing import Any
from uuid import UUID

import httpx

from api.config.affinities_settings import affinities_settings

logger = logging.getLogger(__name__)


class AffinitiesClient:
    """
    Async HTTP client for the NDP Affinities API.

    This client handles registration of datasets, services, and their
    relationships with endpoints in the Affinities system.
    """

    def __init__(self):
        """Initialize the Affinities client with settings."""
        self.settings = affinities_settings
        self.base_url = self.settings.url.rstrip("/")
        self.ep_uuid = self.settings.ep_uuid
        self.timeout = self.settings.timeout

    @property
    def is_enabled(self) -> bool:
        """Check if Affinities integration is enabled and configured."""
        return self.settings.is_configured

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Make an HTTP request to the Affinities API.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, etc.)
        endpoint : str
            API endpoint path (e.g., "/datasets")
        json_data : dict, optional
            JSON body for POST/PUT requests

        Returns
        -------
        dict or None
            Response JSON data, or None on error

        Raises
        ------
        Does not raise; logs errors and returns None
        """
        if not self.is_enabled:
            logger.debug("Affinities integration is disabled, skipping request")
            return None

        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data,
                )
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            logger.error(f"Affinities request timed out: {method} {url}")
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Affinities request failed: {method} {url} - "
                f"Status {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Affinities request error: {method} {url} - {str(e)}")

        return None

    async def register_dataset(
        self,
        title: str,
        metadata: dict[str, Any] | None = None,
    ) -> UUID | None:
        """
        Register a dataset in Affinities.

        Parameters
        ----------
        title : str
            Dataset title
        metadata : dict, optional
            Additional metadata for the dataset

        Returns
        -------
        UUID or None
            The UUID assigned by Affinities, or None on error
        """
        data = {
            "title": title,
            "source_ep": self.ep_uuid,
            "metadata": metadata or {},
        }

        result = await self._request("POST", "/datasets", data)

        if result and "uid" in result:
            dataset_uid = UUID(result["uid"])
            logger.info(f"Registered dataset in Affinities: {dataset_uid}")

            # Create relationship with this endpoint
            await self.create_dataset_endpoint_relationship(dataset_uid)

            return dataset_uid

        return None

    async def register_service(
        self,
        service_type: str | None = None,
        openapi_url: str | None = None,
        version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID | None:
        """
        Register a service in Affinities.

        Parameters
        ----------
        service_type : str, optional
            Type of service (e.g., "api", "proxy")
        openapi_url : str, optional
            URL to the service's OpenAPI specification
        version : str, optional
            Service version
        metadata : dict, optional
            Additional metadata for the service

        Returns
        -------
        UUID or None
            The UUID assigned by Affinities, or None on error
        """
        data = {
            "type": service_type,
            "openapi_url": openapi_url,
            "version": version,
            "source_ep": self.ep_uuid,
            "metadata": metadata or {},
        }

        result = await self._request("POST", "/services", data)

        if result and "uid" in result:
            service_uid = UUID(result["uid"])
            logger.info(f"Registered service in Affinities: {service_uid}")

            # Create relationship with this endpoint
            await self.create_service_endpoint_relationship(service_uid)

            return service_uid

        return None

    async def create_dataset_endpoint_relationship(
        self,
        dataset_uid: UUID,
        role: str = "hosted",
        attrs: dict[str, Any] | None = None,
    ) -> bool:
        """
        Create a relationship between a dataset and this endpoint.

        Parameters
        ----------
        dataset_uid : UUID
            UUID of the dataset in Affinities
        role : str, optional
            Role of the relationship (default: "hosted")
        attrs : dict, optional
            Additional attributes for the relationship

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        data = {
            "dataset_uid": str(dataset_uid),
            "endpoint_uid": self.ep_uuid,
            "role": role,
            "attrs": attrs or {},
        }

        result = await self._request("POST", "/dataset-endpoints", data)
        return result is not None

    async def create_service_endpoint_relationship(
        self,
        service_uid: UUID,
        role: str = "hosted",
        attrs: dict[str, Any] | None = None,
    ) -> bool:
        """
        Create a relationship between a service and this endpoint.

        Parameters
        ----------
        service_uid : UUID
            UUID of the service in Affinities
        role : str, optional
            Role of the relationship (default: "hosted")
        attrs : dict, optional
            Additional attributes for the relationship

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        data = {
            "service_uid": str(service_uid),
            "endpoint_uid": self.ep_uuid,
            "role": role,
            "attrs": attrs or {},
        }

        result = await self._request("POST", "/service-endpoints", data)
        return result is not None


# Global client instance
affinities_client = AffinitiesClient()
