# api/tasks/metrics_task.py

import asyncio
from datetime import datetime
import json
import logging
import os

import httpx

from api.config.catalog_settings import catalog_settings
from api.config.ckan_settings import ckan_settings
from api.config.kafka_settings import kafka_settings
from api.config.minio_settings import s3_settings
from api.config.swagger_settings import swagger_settings
from api.services.status_services import (
    get_num_datasets,
    get_num_services,
    get_public_ip,
    get_services_titles,
    get_system_metrics,
)

logger = logging.getLogger(__name__)


def _is_enabled(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def add_deployment_metrics(metrics_payload):
    """
    Add deployment metadata to the Federation metrics payload.

    Reports connectivity and catalog wiring an operator needs to see an
    Endpoint's setup at a glance: NetBird enablement/address/group (from the
    installer-provided environment), the CKAN URL, and whether a CKAN API key
    is configured.

    No secret or secret-derived value is sent — only a boolean saying a CKAN
    API key is present. The metrics endpoint is not a place for secrets.
    """
    netbird_enabled = _is_enabled(os.getenv("NETBIRD_ENABLED", ""))
    netbird_ip = os.getenv("NETBIRD_IP", "").strip()
    netbird_group = os.getenv("NETBIRD_GROUP", "").strip()

    if netbird_enabled or netbird_ip or netbird_group:
        metrics_payload["netbird_enabled"] = netbird_enabled
        if netbird_ip:
            metrics_payload["netbird_ip"] = netbird_ip
        if netbird_group:
            metrics_payload["netbird_group"] = netbird_group

    ckan_url = (ckan_settings.ckan_url or "").strip()
    if ckan_url:
        metrics_payload["ckan_url"] = ckan_url

    ckan_api_key = (ckan_settings.ckan_api_key or "").strip()
    metrics_payload["ckan_api_key_configured"] = bool(
        ckan_api_key and ckan_api_key != "your-api-key"
    )


async def record_system_metrics():
    """
    Periodically logs the system metrics:
    Public IP, CPU, memory, disk usage, API version, organization, and catalog statistics.

    Additionally, if public=True, posts the metrics JSON to metrics_endpoint.
    """
    while True:
        metrics_payload = {}

        # First: collect and log metrics
        try:
            public_ip = get_public_ip()
            cpu, mem_used, mem_total, disk_used, disk_total = get_system_metrics()

            # Get catalog statistics. An Endpoint with no local catalog has
            # nothing to count; asking for the repository would raise and cost
            # the whole report, including the POST to the Federation.
            if catalog_settings.has_local_catalog:
                catalog_repo = catalog_settings.local_catalog
                num_datasets = get_num_datasets(catalog_repo)
                num_services = get_num_services(catalog_repo)
                services_titles = get_services_titles(catalog_repo)
            else:
                num_datasets = 0
                num_services = 0
                services_titles = []

            # Generate timestamp
            timestamp = datetime.utcnow().isoformat() + "Z"

            metrics_payload = {
                "public_ip": public_ip,
                "cpu": f"{cpu:.1f}%",
                "memory": f"{mem_used:.1f}GB/{mem_total:.1f}GB",
                "disk": f"{disk_used:.1f}GB/{disk_total:.1f}GB",
                "version": swagger_settings.swagger_version,
                "organization": swagger_settings.organization,
                "ep_name": swagger_settings.ep_name,
                "num_datasets": num_datasets,
                "num_services": num_services,
                "services": services_titles,
                "timestamp": timestamp,
                # Infrastructure services
                "jupyterlab_enabled": swagger_settings.use_jupyterlab,
                "kafka_enabled": kafka_settings.kafka_connection,
                "s3_enabled": s3_settings.s3_enabled,
                "pre_ckan_enabled": ckan_settings.pre_ckan_enabled,
            }
            add_deployment_metrics(metrics_payload)

            # Add URLs/details for enabled infrastructure services
            if swagger_settings.use_jupyterlab:
                metrics_payload["jupyterlab_url"] = swagger_settings.jupyter_url
            if kafka_settings.kafka_connection:
                metrics_payload["kafka_host"] = kafka_settings.kafka_host
                metrics_payload["kafka_port"] = kafka_settings.kafka_port

            # Log metrics as JSON
            logger.info(json.dumps(metrics_payload))

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}," f" error: {metrics_payload}")

        # Second try-except for POST request
        if swagger_settings.is_public and metrics_payload:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        swagger_settings.metrics_endpoint,
                        json=metrics_payload,
                        timeout=10,
                    )
                    response.raise_for_status()
                    logger.info(
                        "Successfully posted metrics to "
                        f"{swagger_settings.metrics_endpoint}"
                    )

            except Exception as e:
                logger.error(f"Error posting metrics: {e}")

        # Sleep before next iteration
        await asyncio.sleep(swagger_settings.metrics_interval_seconds)
