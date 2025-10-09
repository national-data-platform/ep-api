# api/services/status_services/check_api_status.py

import logging

from api.config.catalog_settings import catalog_settings
from api.config.ckan_settings import ckan_settings
from api.config.kafka_settings import kafka_settings
from api.config.minio_settings import s3_settings
from api.config.swagger_settings import swagger_settings
from api.services import status_services
from api.services.minio_services.minio_client import minio_client

logger = logging.getLogger(__name__)


def check_backend_connection() -> bool:
    """
    Check if the local catalog backend is reachable and operational.

    Returns
    -------
    bool
        True if backend is connected and healthy, False otherwise
    """
    try:
        # Get the local catalog repository based on current configuration
        repository = catalog_settings.local_catalog
        # Check health using the repository's health check method
        return repository.check_health()
    except Exception as e:
        logger.error(f"Error checking backend connection: {str(e)}")
        return False


def check_pre_ckan_connection() -> bool:
    """
    Check if PreCKAN is reachable and operational.

    Returns
    -------
    bool
        True if PreCKAN is connected and healthy, False otherwise
    """
    try:
        # Get the PreCKAN repository
        repository = catalog_settings.pre_catalog
        # Check health using the repository's health check method
        return repository.check_health()
    except Exception as e:
        logger.error(f"Error checking PreCKAN connection: {str(e)}")
        return False


def check_s3_connection() -> bool:
    """
    Check if S3/MinIO is reachable and operational.

    Returns
    -------
    bool
        True if S3 is connected and healthy, False otherwise
    """
    try:
        return minio_client.test_connection()
    except Exception as e:
        logger.error(f"Error checking S3 connection: {str(e)}")
        return False


def get_status():
    """
    Returns API version, organization, and access control configuration.

    Returns
    -------
    dict
        A dictionary with the API version, organization, and access settings.
    """
    status_dict = {
        "api_version": swagger_settings.swagger_version,
        "organization": swagger_settings.organization,
        "ep_name": swagger_settings.ep_name,
        "organization_based_access": swagger_settings.enable_organization_based_access,
        "local_catalog_backend": catalog_settings.local_catalog_backend,
        "backend_connected": check_backend_connection(),
        "pre_ckan_enabled": ckan_settings.pre_ckan_enabled,
        "kafka_enabled": kafka_settings.kafka_connection,
        "jupyterlab_enabled": swagger_settings.use_jupyterlab,
        "s3_enabled": s3_settings.s3_enabled,
        "auth_api_url": swagger_settings.auth_api_url,
        "metrics_endpoint": swagger_settings.metrics_endpoint,
        "metrics_interval_seconds": swagger_settings.metrics_interval_seconds,
        "is_public": swagger_settings.is_public,
    }

    # Only check PreCKAN connection if it's enabled
    if ckan_settings.pre_ckan_enabled:
        status_dict["pre_ckan_connected"] = check_pre_ckan_connection()

    # Add Kafka connection details if enabled
    if kafka_settings.kafka_connection:
        status_dict["kafka_host"] = kafka_settings.kafka_host
        status_dict["kafka_port"] = kafka_settings.kafka_port

    # Add JupyterLab URL if enabled
    if swagger_settings.use_jupyterlab:
        status_dict["jupyterlab_url"] = swagger_settings.jupyter_url

    # Check S3 connection if enabled
    if s3_settings.s3_enabled:
        status_dict["s3_connected"] = check_s3_connection()

    return status_dict
