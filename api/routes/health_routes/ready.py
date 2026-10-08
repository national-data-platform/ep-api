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

    # No local catalog at all: there is nothing to be unavailable, so the
    # Endpoint is ready without one.
    if not catalog_settings.has_local_catalog:
        return {"status": "disabled", "backend": backend}

    # CKAN_LOCAL_ENABLED is the master switch for the local catalog on every
    # backend: with it off the local catalog routes are not mounted and
    # /search rejects server=local, so nothing can reach the catalog. Probing
    # it would report a dependency the Endpoint never uses as down, and answer
    # 503 for a deployment running exactly as configured.
    if not ckan_settings.ckan_local_enabled:
        return {"status": "disabled", "backend": backend}

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

    # Reported alongside the connection because a reachable staging catalog
    # still refuses every publish when this is unset: the dataset keeps its
    # local organization, which those credentials rarely own. Detail rather
    # than a failure, since deployments whose staging catalog holds the same
    # organizations work without it (issue #274).
    organization_configured = bool(ckan_settings.pre_ckan_organization)

    try:
        repo = catalog_settings.pre_catalog
        return {
            **_check_with_latency(repo.check_health),
            "organization_configured": organization_configured,
        }
    except Exception as e:
        return {
            "status": "down",
            "error": str(e),
            "organization_configured": organization_configured,
        }


async def _check_affinities() -> Dict[str, Any]:
    """
    Check Affinities and whether it knows AFFINITIES_EP_UUID.

    Reported because nothing else surfaced a wrong UUID: the value is issued
    by Affinities and never verified here, so an endpoint that was never
    registered kept recording datasets nobody could attribute to it, and
    every response said the registration had succeeded (issue #281).
    """
    from api.services.affinities_services import AffinitiesClient

    client = AffinitiesClient()
    if not client.is_enabled:
        return {"status": "disabled"}

    start = time.time()
    probe = await client.check_registration()
    latency_ms = round((time.time() - start) * 1000, 2)

    if not probe["reachable"]:
        return {
            "status": "down",
            "latency_ms": latency_ms,
            "error": probe["detail"],
        }

    result: Dict[str, Any] = {
        "status": "up",
        "latency_ms": latency_ms,
        "endpoint_registered": probe["endpoint_registered"],
    }

    # Kept out of "error": Affinities answered, so the check itself did not
    # fail. What is wrong is this Endpoint's configuration.
    if probe["detail"]:
        result["detail"] = probe["detail"]

    return result


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
                # kafka-python 3 renamed api_version_auto_timeout_ms.
                bootstrap_timeout_ms=5000,
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
        "affinities": await _check_affinities(),
    }

    # Affinities is reported but deliberately left out of the verdict. No
    # request ever reads from it, so an orchestrator taking the container out
    # of rotation over it would stop serving the catalog for a system that
    # serves no traffic -- and doing so would turn a deployment that is
    # healthy today into a 503 purely because it has the integration on.
    # Same reason an unknown endpoint UUID is a detail rather than a failure:
    # it is reported so it stops being invisible, not enforced (issue #281).
    required = {name: c for name, c in checks.items() if name != "affinities"}

    # Determine overall status - only fail if an enabled service is down
    all_healthy = all(
        check.get("status") in ("up", "disabled") for check in required.values()
    )

    overall_status = "healthy" if all_healthy else "unhealthy"

    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks": checks,
    }
