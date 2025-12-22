# api/tasks/metrics_task.py

import asyncio
from datetime import datetime
import json
import logging

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

            # Get catalog statistics
            catalog_repo = catalog_settings.local_catalog
            num_datasets = get_num_datasets(catalog_repo)
            num_services = get_num_services(catalog_repo)
            services_titles = get_services_titles(catalog_repo)

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
