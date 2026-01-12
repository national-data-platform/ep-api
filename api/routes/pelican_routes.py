# api/routes/pelican_routes.py
"""
API routes for Pelican federation access (Phase 1).

These endpoints allow browsing and downloading from external Pelican federations.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from api.repositories.pelican_repository import PelicanRepository
from api.services.pelican_services.browse_federation import (
    browse_namespace,
    get_file_info,
)
from api.services.pelican_services.download_file import download_file, stream_file
from api.services.pelican_services.import_metadata import import_file_as_resource
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pelican", tags=["Pelican Federation"])


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


@router.post("/import-metadata")
async def import_metadata(request: ImportMetadataRequest):
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
