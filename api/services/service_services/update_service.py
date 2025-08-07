# api/services/service_services/update_service.py
from typing import Any, Dict, Optional

from api.config import ckan_settings

RESERVED_KEYS = {
    "name",
    "title",
    "owner_org",
    "notes",
    "id",
    "resources",
    "collection",
    "service_url",
    "service_type",
    "health_check_url",
    "documentation_url",
}


def update_service(
    service_id: str,
    service_name: Optional[str] = None,
    service_title: Optional[str] = None,
    owner_org: Optional[str] = None,
    service_url: Optional[str] = None,
    service_type: Optional[str] = None,
    notes: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
    health_check_url: Optional[str] = None,
    documentation_url: Optional[str] = None,
    ckan_instance=None,
) -> str:
    """
    Update an existing service in CKAN (full replacement).

    Parameters
    ----------
    service_id : str
        The unique identifier of the service to update.
    service_name : Optional[str]
        The unique name of the service.
    service_title : Optional[str]
        The display title of the service.
    owner_org : Optional[str]
        The ID of the organization (must be 'services').
    service_url : Optional[str]
        The URL where the service is accessible.
    service_type : Optional[str]
        The type of service (e.g., 'API', 'Web Service', 'Microservice').
    notes : Optional[str]
        Additional notes about the service.
    extras : Optional[Dict[str, Any]]
        Additional metadata as key-value pairs.
    health_check_url : Optional[str]
        URL for service health check endpoint.
    documentation_url : Optional[str]
        URL to service documentation.
    ckan_instance : optional
        A CKAN instance to use for service update. If not provided,
        uses the default `ckan_settings.ckan`.

    Returns
    -------
    str
        The ID of the updated service.

    Raises
    ------
    ValueError
        If owner_org is provided and is not 'services', or if extras is
        not a dictionary.
    KeyError
        If extras contains reserved keys.
    Exception
        For errors during service update.
    """
    if ckan_instance is None:
        ckan_instance = ckan_settings.ckan

    # Validate owner_org if provided
    if owner_org is not None and owner_org != "services":
        raise ValueError("owner_org must be 'services' for service registration")

    # Validate extras
    if extras and not isinstance(extras, dict):
        raise ValueError("Extras must be a dictionary or None.")

    if extras and RESERVED_KEYS.intersection(extras):
        raise KeyError(
            "Extras contain reserved keys: " f"{RESERVED_KEYS.intersection(extras)}"
        )

    try:
        # Fetch the existing service
        service = ckan_instance.action.package_show(id=service_id)
    except Exception as exc:
        raise Exception(f"Error fetching service: {str(exc)}")

    # Update fields with new values or keep existing ones
    service["name"] = service_name or service.get("name")
    service["title"] = service_title or service.get("title")
    service["owner_org"] = owner_org or service.get("owner_org")

    if notes is not None:
        service["notes"] = notes

    # Handle extras - merge with existing if provided
    if extras is not None:
        current_extras = {
            extra["key"]: extra["value"] for extra in service.get("extras", [])
        }

        # Prepare service-specific extras
        service_extras = {}
        if service_type is not None:
            service_extras["service_type"] = service_type
        if health_check_url is not None:
            service_extras["health_check_url"] = health_check_url
        if documentation_url is not None:
            service_extras["documentation_url"] = documentation_url

        # Merge user extras with service-specific extras
        current_extras.update(extras)
        current_extras.update(service_extras)

        service["extras"] = [{"key": k, "value": v} for k, v in current_extras.items()]
    else:
        # Handle service-specific fields even if no user extras
        current_extras = {
            extra["key"]: extra["value"] for extra in service.get("extras", [])
        }

        updated = False
        if service_type is not None:
            current_extras["service_type"] = service_type
            updated = True
        if health_check_url is not None:
            current_extras["health_check_url"] = health_check_url
            updated = True
        if documentation_url is not None:
            current_extras["documentation_url"] = documentation_url
            updated = True

        if updated:
            service["extras"] = [
                {"key": k, "value": v} for k, v in current_extras.items()
            ]

    # Update the service URL in resources if provided
    if service_url is not None:
        for resource in service.get("resources", []):
            if resource.get("format") == "service":
                resource["url"] = service_url
                # Update resource description
                resource["description"] = (
                    f"Service endpoint for {service.get('title', service_name)} "
                    f"accessible at {service_url}"
                )
                break

    try:
        updated_service = ckan_instance.action.package_update(**service)
        return updated_service["id"]
    except Exception as exc:
        raise Exception(f"Error updating service: {str(exc)}")


def patch_service(
    service_id: str,
    service_name: Optional[str] = None,
    service_title: Optional[str] = None,
    owner_org: Optional[str] = None,
    service_url: Optional[str] = None,
    service_type: Optional[str] = None,
    notes: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
    health_check_url: Optional[str] = None,
    documentation_url: Optional[str] = None,
    ckan_instance=None,
) -> str:
    """
    Partially update an existing service in CKAN.

    Only updates the fields that are provided, leaving others unchanged.
    This is ideal for making small updates without needing to provide
    the complete service information.

    Parameters
    ----------
    service_id : str
        The unique identifier of the service to patch.
    service_name : Optional[str]
        The unique name of the service.
    service_title : Optional[str]
        The display title of the service.
    owner_org : Optional[str]
        The ID of the organization (must be 'services').
    service_url : Optional[str]
        The URL where the service is accessible.
    service_type : Optional[str]
        The type of service (e.g., 'API', 'Web Service', 'Microservice').
    notes : Optional[str]
        Additional notes about the service.
    extras : Optional[Dict[str, Any]]
        Additional metadata to merge with existing.
    health_check_url : Optional[str]
        URL for service health check endpoint.
    documentation_url : Optional[str]
        URL to service documentation.
    ckan_instance : optional
        A CKAN instance to use for service patch. If not provided,
        uses the default `ckan_settings.ckan`.

    Returns
    -------
    str
        The ID of the patched service.

    Raises
    ------
    ValueError
        If owner_org is provided and is not 'services', or if extras is
        not a dictionary.
    KeyError
        If extras contains reserved keys.
    Exception
        For errors during service patch.
    """
    if ckan_instance is None:
        ckan_instance = ckan_settings.ckan

    # Validate owner_org if provided
    if owner_org is not None and owner_org != "services":
        raise ValueError("owner_org must be 'services' for service registration")

    # Validate extras
    if extras and not isinstance(extras, dict):
        raise ValueError("Extras must be a dictionary or None.")

    if extras and RESERVED_KEYS.intersection(extras):
        raise KeyError(
            "Extras contain reserved keys: " f"{RESERVED_KEYS.intersection(extras)}"
        )

    try:
        # Fetch the existing service
        service = ckan_instance.action.package_show(id=service_id)
    except Exception as exc:
        raise Exception(f"Error fetching service: {str(exc)}")

    # Update fields with new values if provided
    if service_name is not None:
        service["name"] = service_name
    if service_title is not None:
        service["title"] = service_title
    if owner_org is not None:
        service["owner_org"] = owner_org
    if notes is not None:
        service["notes"] = notes

    # Handle extras - merge with existing if provided
    current_extras = {
        extra["key"]: extra["value"] for extra in service.get("extras", [])
    }

    # Update service-specific extras if provided
    if service_type is not None:
        current_extras["service_type"] = service_type
    if health_check_url is not None:
        current_extras["health_check_url"] = health_check_url
    if documentation_url is not None:
        current_extras["documentation_url"] = documentation_url

    # Merge user extras with existing/service extras if provided
    if extras is not None:
        current_extras.update(extras)

    service["extras"] = [{"key": k, "value": v} for k, v in current_extras.items()]

    # Update the service URL in resources if provided
    if service_url is not None:
        for resource in service.get("resources", []):
            if resource.get("format") == "service":
                resource["url"] = service_url
                # Update resource description
                resource["description"] = (
                    f"Service endpoint for {service.get('title', service_name)} "
                    f"accessible at {service_url}"
                )
                break

    try:
        updated_service = ckan_instance.action.package_update(**service)
        return updated_service["id"]
    except Exception as exc:
        raise Exception(f"Error updating service: {str(exc)}")
