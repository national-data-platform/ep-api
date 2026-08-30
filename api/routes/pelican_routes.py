# api/routes/pelican_routes.py
"""
API routes for Pelican federation access (Phase 1).

These endpoints allow browsing and downloading from external Pelican federations.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from api.repositories.pelican_repository import PelicanRepository
from api.services.pelican_services.browse_federation import (
    browse_namespace,
    get_file_info,
)
from api.services.pelican_services.download_file import download_file, stream_file
from api.services.pelican_services.read_file import read_object
from api.services.pelican_services.event_subscription import (
    EventSubscriptionUnavailable,
    broker,
    load_config,
)
from api.services.pelican_services.import_metadata import import_file_as_resource
from api.services.auth_services import (
    get_user_for_read_operation,
    get_user_for_write_operation,
)
import json
import logging
import os

logger = logging.getLogger(__name__)

# Largest object /pelican/read will return inline. Anything bigger is a
# download, not a read: the contents go into the response body, so an
# unbounded read would put an arbitrary object into the endpoint's memory.
DEFAULT_MAX_READ_BYTES = 10 * 1024 * 1024

# The read gate is declared on the router rather than on each route: these
# endpoints shipped completely unauthenticated (issue #261), and a
# router-level dependency means a route added later cannot silently miss it.
# Routes that write take the stricter write dependency on top of this one.
router = APIRouter(
    prefix="/pelican",
    tags=["Pelican Federation"],
    dependencies=[Depends(get_user_for_read_operation)],
)


# Pydantic models
class ImportMetadataRequest(BaseModel):
    pelican_url: str
    package_id: str
    resource_name: Optional[str] = None
    resource_description: Optional[str] = None


# Helper function to get Pelican repository
def get_pelican_repo(federation: str = "osdf") -> PelicanRepository:
    """
    Get Pelican repository for specified federation.

    Parameters
    ----------
    federation : str
        Federation name (default "osdf")

    Returns
    -------
    PelicanRepository
        Initialized repository
    """
    # Federation URLs mapping
    federations = {
        "osdf": "pelican://osg-htc.org",
        "path-cc": "pelican://path-cc.io",
        # Add more federations as needed
    }

    federation_url = os.getenv("PELICAN_FEDERATION_URL") or federations.get(
        federation.lower(), federations["osdf"]
    )

    return PelicanRepository(
        federation_url=federation_url,
        direct_reads=os.getenv("PELICAN_DIRECT_READS", "false").lower() == "true",
    )


@router.get("/federations")
async def list_federations():
    """
    List available Pelican federations.

    Returns
    -------
    dict
        List of available federations with their URLs
    """
    federations = {
        "osdf": {
            "name": "Open Science Data Federation",
            "url": "pelican://osg-htc.org",
            "description": "Primary federation for scientific data sharing",
        },
        "path-cc": {
            "name": "PATh Credit Compute",
            "url": "pelican://path-cc.io",
            "description": "PATh Facility data federation",
        },
    }

    # Check if custom federation URL is configured
    custom_url = os.getenv("PELICAN_FEDERATION_URL")
    if custom_url:
        federations["custom"] = {
            "name": "Custom Federation",
            "url": custom_url,
            "description": "Configured via PELICAN_FEDERATION_URL",
        }

    return {"success": True, "federations": federations, "count": len(federations)}


@router.get("/browse")
async def browse_files(
    path: str = Query(..., description="Namespace path to browse"),
    federation: str = Query("osdf", description="Federation to query"),
    detail: bool = Query(False, description="Include detailed file information"),
):
    """
    Browse files in a Pelican federation namespace.

    Parameters
    ----------
    path : str
        Namespace path (e.g., "/ospool/uc-shared/public")
    federation : str
        Federation name (default "osdf")
    detail : bool
        If True, return detailed file information

    Returns
    -------
    dict
        Files in the namespace
    """
    try:
        pelican_repo = get_pelican_repo(federation)
        result = browse_namespace(pelican_repo, path, detail=detail)

        if not result["success"]:
            raise HTTPException(
                status_code=404, detail=result.get("error", "Path not found")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing Pelican path {path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error browsing path: {str(e)}")


@router.get("/info")
async def get_info(
    path: str = Query(..., description="File path"),
    federation: str = Query("osdf", description="Federation to query"),
):
    """
    Get metadata for a file without downloading it.

    Parameters
    ----------
    path : str
        File path
    federation : str
        Federation name

    Returns
    -------
    dict
        File metadata (name, size, type, modified time)
    """
    try:
        pelican_repo = get_pelican_repo(federation)
        result = get_file_info(pelican_repo, path)

        if not result["success"]:
            raise HTTPException(
                status_code=404, detail=result.get("error", "File not found")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info for {path}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting file info: {str(e)}"
        )


@router.get("/download")
async def download(
    path: str = Query(..., description="File path to download"),
    federation: str = Query("osdf", description="Federation to query"),
    stream: bool = Query(
        False, description="Stream file instead of downloading all at once"
    ),
):
    """
    Download a file from Pelican federation.

    Parameters
    ----------
    path : str
        File path to download
    federation : str
        Federation name
    stream : bool
        If True, stream file content; if False, download entire file

    Returns
    -------
    File contents (binary)
    """
    try:
        pelican_repo = get_pelican_repo(federation)

        if stream:
            # Stream file content
            file_handle = stream_file(pelican_repo, path)
            filename = os.path.basename(path)

            return StreamingResponse(
                file_handle,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        else:
            # Download entire file
            contents = download_file(pelican_repo, path)
            filename = os.path.basename(path)

            return Response(
                content=contents,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

    except Exception as e:
        logger.error(f"Error downloading file {path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


def _max_read_bytes() -> int:
    """
    Resolve the inline read limit from ``PELICAN_MAX_READ_BYTES``.

    Settings are declared with ``extra: "allow"``, so a malformed value
    reaches this point instead of failing at startup; fall back to the
    default rather than letting a typo disable the limit.

    Returns
    -------
    int
        Limit in bytes.
    """
    raw = os.getenv("PELICAN_MAX_READ_BYTES", "")
    if not raw:
        return DEFAULT_MAX_READ_BYTES
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            f"PELICAN_MAX_READ_BYTES is not an integer ({raw!r}); "
            f"using {DEFAULT_MAX_READ_BYTES}."
        )
        return DEFAULT_MAX_READ_BYTES
    if value <= 0:
        logger.warning(
            f"PELICAN_MAX_READ_BYTES must be positive (got {value}); "
            f"using {DEFAULT_MAX_READ_BYTES}."
        )
        return DEFAULT_MAX_READ_BYTES
    return value


@router.get("/read")
async def read_file_contents(
    path: str = Query(..., description="Path of the object to read"),
    federation: str = Query("osdf", description="Federation to query"),
):
    """
    Read a Pelican object and return its contents in the response body.

    ``/download`` hands back a file to save; this returns the contents
    inline so they can be piped straight into the caller's own code.

    Parameters
    ----------
    path : str
        Path of the object to read
    federation : str
        Federation name (default "osdf")

    Returns
    -------
    dict
        ``path``, ``size``, ``encoding`` ("utf-8" or "base64") and
        ``content``

    Raises
    ------
    HTTPException
        - 404: Object not found in the federation
        - 413: Object larger than the inline read limit
        - 502: The federation could not be reached
    """
    try:
        pelican_repo = get_pelican_repo(federation)
        result = read_object(pelican_repo, path, _max_read_bytes())

        if not result["success"]:
            status_by_reason = {
                "not_found": 404,
                "too_large": 413,
                "unavailable": 502,
            }
            raise HTTPException(
                status_code=status_by_reason.get(result.get("reason"), 502),
                detail=result["error"],
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading Pelican object {path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading object: {str(e)}")


def _sse(event: str, payload: dict) -> str:
    """Format one Server-Sent Event message."""
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.get("/subscribe")
async def subscribe_to_events(
    request: Request,
    event_source: str = Query(
        ..., description="Namespace to watch, e.g. osdf/vdc/public/data"
    ),
):
    """
    Stream Pelican file events as Server-Sent Events.

    The Endpoint holds one upstream subscription per event source and
    fans it out, so every listener on a source receives every event
    rather than competing for them.

    Each event arrives as an ``event: file`` message whose data carries
    the object's ``name``, ``url``, ``size`` and ``mod_time``. The
    ``url`` can be handed straight to ``/pelican/read`` to get the
    contents, or to ``/pelican/download`` to fetch it as a file.

    A ``: keepalive`` comment is sent during quiet periods, so a proxy
    does not mistake an idle stream for a dead one.

    Parameters
    ----------
    request : Request
        Used to notice that the caller has gone away.
    event_source : str
        Namespace to watch.

    Returns
    -------
    StreamingResponse
        A ``text/event-stream``.

    Raises
    ------
    HTTPException
        503 if the event server is not configured on this Endpoint.
    """
    try:
        config = load_config()
    except EventSubscriptionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    async def event_stream():
        # Sent immediately, so the caller can tell the stream is open
        # even while the namespace is quiet.
        yield ": subscribed\n\n"
        try:
            async for event in broker.listen(event_source, config):
                if await request.is_disconnected():
                    break
                if event is None:
                    yield ": keepalive\n\n"
                    continue
                yield _sse("file", event)
        except EventSubscriptionUnavailable as exc:
            yield _sse("error", {"detail": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"Pelican event stream failed: {exc}")
            yield _sse("error", {"detail": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Without this nginx buffers the stream and holds events
            # back until the buffer fills, defeating the point.
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/subscriptions")
async def list_subscriptions():
    """
    Report the upstream subscriptions this Endpoint currently holds.

    Returns
    -------
    dict
        One entry per event source with its connection state, listener
        count, and how many events were dropped for slow listeners.
    """
    return {"success": True, "subscriptions": broker.status()}


@router.post("/import-metadata")
async def import_metadata(
    request: ImportMetadataRequest,
    _user=Depends(get_user_for_write_operation),
):
    """
    Import a Pelican file as a resource in the local catalog.

    This allows you to register external Pelican files in your local catalog
    so they appear in searches and can be managed alongside local resources.

    Parameters
    ----------
    request : ImportMetadataRequest
        Import request with pelican_url, package_id, and optional metadata

    Returns
    -------
    dict
        Created resource data
    """
    try:
        # Extract federation from URL
        if not request.pelican_url.startswith("pelican://"):
            raise HTTPException(
                status_code=400, detail="URL must start with pelican://"
            )

        federation_part = request.pelican_url.replace("pelican://", "").split("/")[0]

        # Map federation hostname to our federation names
        federation_map = {"osg-htc.org": "osdf", "path-cc.io": "path-cc"}
        federation = federation_map.get(federation_part, "osdf")

        pelican_repo = get_pelican_repo(federation)

        result = import_file_as_resource(
            pelican_repo=pelican_repo,
            pelican_url=request.pelican_url,
            package_id=request.package_id,
            resource_name=request.resource_name,
            resource_description=request.resource_description,
        )

        if not result["success"]:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Import failed")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Error importing: {str(e)}")
