# api/routes/health_routes/ready.py

import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Response, status

from api.config.catalog_settings import catalog_settings
from api.config.ckan_settings import ckan_settings
from api.config.kafka_settings import kafka_settings
from api.config.minio_settings import s3_settings

router = APIRouter()


def _check_with_latency(check_func) -> Dict[str, Any]:
    """Execute a health check and measure latency."""
    start = time.time()
    try:
        result = check_func()
        latency_ms = round((time.time() - start) * 1000, 2)
        if result:
            return {"status": "up", "latency_ms": latency_ms}
        else:
            return {"status": "down", "latency_ms": latency_ms, "error": "Check failed"}
    except Exception as e:
        latency_ms = round((time.time() - start) * 1000, 2)
        return {"status": "down", "latency_ms": latency_ms, "error": str(e)}


def _check_minio() -> Dict[str, Any]:
    """Check MinIO/S3 connection."""
    if not s3_settings.is_configured:
        return {"status": "disabled"}

    from api.services.minio_services.minio_client import minio_client

    return _check_with_latency(minio_client.test_connection)


def _check_local_catalog() -> Dict[str, Any]:
    """Check local catalog (CKAN or MongoDB) connection."""
    backend = catalog_settings.local_catalog_backend.lower()

    if backend == "ckan" and not ckan_settings.ckan_local_enabled:
        return {"status": "disabled", "backend": "ckan"}

    try:
        repo = catalog_settings.local_catalog
        return {
            **_check_with_latency(repo.check_health),
            "backend": backend,
        }
    except Exception as e:
        return {"status": "down", "backend": backend, "error": str(e)}


def _check_pre_ckan() -> Dict[str, Any]:
    """Check PreCKAN connection."""
    if not ckan_settings.pre_ckan_enabled:
        return {"status": "disabled"}

    if not ckan_settings.pre_ckan_url or not ckan_settings.pre_ckan_api_key:
        return {"status": "disabled"}

    try:
        repo = catalog_settings.pre_catalog
        return _check_with_latency(repo.check_health)
    except Exception as e:
        return {"status": "down", "error": str(e)}


def _check_kafka() -> Dict[str, Any]:
    """Check Kafka connection."""
    if not kafka_settings.kafka_connection:
        return {"status": "disabled"}

    def kafka_check():
        from kafka import KafkaProducer
        from kafka.errors import KafkaError

        try:
            producer = KafkaProducer(
                bootstrap_servers=f"{kafka_settings.kafka_host}:{kafka_settings.kafka_port}",
                request_timeout_ms=5000,
                api_version_auto_timeout_ms=5000,
            )
            producer.close()
            return True
        except KafkaError:
            return False

    return _check_with_latency(kafka_check)


@router.get(
    "/ready",
    summary="Readiness check (readiness probe)",
    description=(
        "Returns HTTP 200 if all configured dependencies are available. "
        "Returns HTTP 503 if any required dependency is unavailable. "
        "Used by container orchestrators to determine if the container can receive traffic."
    ),
    tags=["Health"],
)
async def readiness_check(response: Response):
    """
    Readiness probe endpoint.

    Checks all configured dependencies and returns their status.
    Returns HTTP 503 if any enabled dependency is down.

    Returns
    -------
    dict
        Readiness status with individual dependency checks.
    """
    checks = {
        "local_catalog": _check_local_catalog(),
        "pre_ckan": _check_pre_ckan(),
        "minio": _check_minio(),
        "kafka": _check_kafka(),
    }

    # Determine overall status - only fail if an enabled service is down
    all_healthy = all(
        check.get("status") in ("up", "disabled") for check in checks.values()
    )

    overall_status = "healthy" if all_healthy else "unhealthy"

    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks": checks,
    }
