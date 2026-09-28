# api/services/affinities_services/affinities_client.py
"""
HTTP client for NDP Affinities API.

This module provides an async client for registering datasets, services,
and their relationships with the Affinities system.
"""

import logging
import time
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

    # Upper bound for the readiness probe; see check_registration.
    READINESS_TIMEOUT_SECONDS = 5.0

    # How long a probe result is reused. /ready is called on a schedule and
    # the answer -- does Affinities know this endpoint -- changes only when
    # somebody edits configuration, while an unreachable Affinities costs
    # whole seconds per call. Without this, reporting Affinities could make
    # the readiness probe itself time out and take the container out of
    # rotation, which is the outcome leaving it out of the verdict exists to
    # avoid (issue #281).
    REGISTRATION_CACHE_SECONDS = 30.0

    # Class level on purpose: /ready builds a new client per request, so
    # anything kept on the instance would never be read again.
    _registration_cache: dict[str, Any] | None = None

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

    def _log_failed_link(self, kind: str, uid: UUID) -> None:
        """
        Report a refused link, naming the endpoint it was refused for.

        Parameters
        ----------
        kind : str
            Either "dataset" or "service".
        uid : UUID
            UUID of the record that could not be linked.
        """
        # _request already logged the transport failure, but not what it
        # cost: the record stays in Affinities attributed to nobody. The
        # cause is almost always configuration, so the log says which
        # setting to look at (issue #281).
        logger.error(
            f"Affinities refused to link {kind} {uid} to endpoint "
            f"{self.ep_uuid}. The {kind} is registered in Affinities but is "
            "not attributed to this Endpoint. The likeliest cause is an "
            "AFFINITIES_EP_UUID this Affinities instance does not know: the "
            "value is issued by Affinities when the endpoint is registered "
            "there, and nothing here ever checked it. GET /ready reports "
            "whether it is known."
        )

    async def check_registration(self) -> dict[str, Any]:
        """
        Report whether Affinities is reachable and knows this endpoint.

        Returns
        -------
        dict
            ``reachable`` is True when Affinities answered at all.
            ``endpoint_registered`` is True when it knows
            ``AFFINITIES_EP_UUID``, False when it answered that no such
            endpoint exists, and None when the question could not be
            answered. ``detail`` explains a non-True outcome.
        """
        # Keyed on what the answer depends on, so changing either is not
        # masked by a result cached for the previous value.
        key = f"{self.base_url}/ep/{self.ep_uuid}"

        cached = self._cached_registration(key)
        if cached is not None:
            return cached

        probe = await self._probe_registration(key)
        type(self)._registration_cache = {
            "key": key,
            "at": time.monotonic(),
            "probe": probe,
        }
        return probe

    @classmethod
    def _cached_registration(cls, key: str) -> dict[str, Any] | None:
        """Return a still-valid probe result for ``key``, if there is one."""
        cached = cls._registration_cache

        if cached is None or cached["key"] != key:
            return None

        if time.monotonic() - cached["at"] > cls.REGISTRATION_CACHE_SECONDS:
            return None

        return cached["probe"]

    async def _probe_registration(self, url: str) -> dict[str, Any]:
        """Ask Affinities about this endpoint. See check_registration."""
        # Deliberately shorter than the configured timeout: this runs on
        # every readiness probe, and waiting the 30s default on a system
        # that serves no request would make the probe itself the problem.
        timeout = min(self.timeout, self.READINESS_TIMEOUT_SECONDS)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
        except Exception as exc:
            reason = str(exc) or type(exc).__name__
            return {
                "reachable": False,
                "endpoint_registered": None,
                "detail": f"{type(exc).__name__}: {reason}",
            }

        if response.status_code == 200:
            return {
                "reachable": True,
                "endpoint_registered": True,
                "detail": None,
            }

        if response.status_code == 404:
            return {
                "reachable": True,
                "endpoint_registered": False,
                "detail": (
                    f"Affinities does not know endpoint {self.ep_uuid}. "
                    "Datasets and services registered from here cannot be "
                    "linked to it, so they are recorded attributed to "
                    "nobody. Register this Endpoint with POST /ep on "
                    "Affinities and set AFFINITIES_EP_UUID to the UUID it "
                    "returns."
                ),
            }

        # Anything else, such as the 422 a malformed UUID produces:
        # Affinities is up, but the question went unanswered.
        return {
            "reachable": True,
            "endpoint_registered": None,
            "detail": (
                f"Affinities answered {response.status_code} when asked "
                f"about endpoint {self.ep_uuid}"
            ),
        }

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

            # The triple is only meaningful once the dataset is reachable
            # from this endpoint. Building it on top of a failed link left a
            # triple naming an endpoint Affinities does not have, and the
            # registration still reported success (issue #281).
            if await self.create_dataset_endpoint_relationship(dataset_uid):
                await self.create_affinity_triple(dataset_uid=dataset_uid)
            else:
                logger.error(
                    "Skipping the affinity triple for dataset "
                    f"{dataset_uid}: it is not linked to endpoint "
                    f"{self.ep_uuid}, so the triple would point at a "
                    "relationship that does not exist."
                )

            # Returned even when the link failed: this UUID is the only way
            # back to the record Affinities just created, and the caller
            # stores it on the dataset as ndp_affinity_uuid.
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

            # See register_dataset: an unlinked record must not get a
            # triple (issue #281).
            if await self.create_service_endpoint_relationship(service_uid):
                await self.create_affinity_triple(service_uid=service_uid)
            else:
                logger.error(
                    "Skipping the affinity triple for service "
                    f"{service_uid}: it is not linked to endpoint "
                    f"{self.ep_uuid}, so the triple would point at a "
                    "relationship that does not exist."
                )

            # Returned even when the link failed, so the caller keeps a
            # reference to the record that was created.
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

        if result is None:
            self._log_failed_link("dataset", dataset_uid)
            return False

        return True

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

        if result is None:
            self._log_failed_link("service", service_uid)
            return False

        return True

    async def create_affinity_triple(
        self,
        dataset_uid: UUID | None = None,
        service_uid: UUID | None = None,
        attrs: dict[str, Any] | None = None,
        version: int | None = None,
    ) -> UUID | None:
        """
        Create an affinity triple linking dataset/service with this endpoint.

        Parameters
        ----------
        dataset_uid : UUID, optional
            UUID of the dataset in Affinities
        service_uid : UUID, optional
            UUID of the service in Affinities
        attrs : dict, optional
            Additional attributes for the affinity
        version : int, optional
            Version number for the affinity

        Returns
        -------
        UUID or None
            The UUID of the created affinity triple, or None on error
        """
        data = {
            "endpoint_uids": [self.ep_uuid],
            "attrs": attrs or {},
        }

        if dataset_uid:
            data["dataset_uid"] = str(dataset_uid)
        if service_uid:
            data["service_uids"] = [str(service_uid)]
        if version is not None:
            data["version"] = version

        result = await self._request("POST", "/affinities", data)

        if result and "triple_uid" in result:
            triple_uid = UUID(result["triple_uid"])
            logger.info(f"Created affinity triple in Affinities: {triple_uid}")
            return triple_uid

        return None


# Global client instance
affinities_client = AffinitiesClient()
