# api/routes/health_routes/health.py

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Health check (liveness probe)",
    description=(
        "Returns HTTP 200 if the API process is running. "
        "Used by container orchestrators to determine if the container needs restart."
    ),
    tags=["Health"],
)
async def health_check():
    """
    Liveness probe endpoint.

    Returns a simple health status indicating the API is running.
    This endpoint does not check dependencies - use /ready for that.

    Returns
    -------
    dict
        Health status with timestamp.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
