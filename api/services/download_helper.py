# api/services/download_helper.py
"""
Helper service for downloading resources from various backends.

This module provides a unified interface for downloading resources from
different storage backends including HTTP/HTTPS, S3, Kafka, and Pelican.
"""

from typing import Tuple, Optional, BinaryIO
from api.repositories.pelican_repository import PelicanRepository
import logging
import os
import httpx

logger = logging.getLogger(__name__)


def is_pelican_url(url: str) -> bool:
    """
    Check if a URL is a Pelican federation URL.

    Parameters
    ----------
    url : str
        URL to check

    Returns
    -------
    bool
        True if URL starts with pelican://
    """
    return url.startswith("pelican://")


def get_pelican_repo_for_url(url: str) -> PelicanRepository:
    """
    Get appropriate Pelican repository for a given URL.

    Parameters
    ----------
    url : str
        Pelican URL (e.g., pelican://osg-htc.org/path/to/file)

    Returns
    -------
    PelicanRepository
        Initialized repository for the federation
    """
    # Extract federation from URL
    # Format: pelican://federation-host/path/to/file
    if not url.startswith("pelican://"):
        raise ValueError("URL must start with pelican://")

    federation_part = url.replace("pelican://", "").split("/")[0]

    # Construct federation URL
    federation_url = f"pelican://{federation_part}"

    return PelicanRepository(
        federation_url=federation_url,
        direct_reads=os.getenv("PELICAN_DIRECT_READS", "false").lower() == "true",
    )


async def download_resource(url: str) -> Tuple[bytes, Optional[str]]:
    """
    Download resource from any supported backend.

    This function detects the URL scheme and delegates to the appropriate
    download handler (HTTP, Pelican, S3, etc.).

    Parameters
    ----------
    url : str
        Resource URL

    Returns
    -------
    tuple
        (content: bytes, error: str or None)
    """
    try:
        if is_pelican_url(url):
            # Handle Pelican URLs
            return await download_from_pelican(url)
        elif url.startswith(("http://", "https://")):
            # Handle HTTP/HTTPS URLs
            return await download_from_http(url)
        elif url.startswith("s3://"):
            # Handle S3 URLs (future implementation)
            return None, "S3 downloads not yet implemented in this helper"
        else:
            return None, f"Unsupported URL scheme: {url}"

    except Exception as e:
        logger.error(f"Error downloading resource from {url}: {e}")
        return None, str(e)


async def download_from_pelican(url: str) -> Tuple[bytes, Optional[str]]:
    """
    Download file from Pelican federation.

    Parameters
    ----------
    url : str
        Pelican URL (e.g., pelican://osg-htc.org/ospool/data/file.nc)

    Returns
    -------
    tuple
        (content: bytes, error: str or None)
    """
    try:
        pelican_repo = get_pelican_repo_for_url(url)

        # Extract path from URL
        # Format: pelican://federation/path/to/file → /path/to/file
        path = "/" + url.replace("pelican://", "").split("/", 1)[1]

        logger.info(f"Downloading from Pelican: {url} (path: {path})")
        content = pelican_repo.read_file(path)

        logger.info(f"Successfully downloaded {len(content)} bytes from Pelican")
        return content, None

    except Exception as e:
        logger.error(f"Error downloading from Pelican {url}: {e}")
        return None, f"Pelican download error: {str(e)}"


async def download_from_http(url: str) -> Tuple[bytes, Optional[str]]:
    """
    Download file from HTTP/HTTPS URL.

    Parameters
    ----------
    url : str
        HTTP or HTTPS URL

    Returns
    -------
    tuple
        (content: bytes, error: str or None)
    """
    try:
        logger.info(f"Downloading from HTTP: {url}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            content = response.content
            logger.info(f"Successfully downloaded {len(content)} bytes from HTTP")
            return content, None

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading {url}: {e.response.status_code}")
        return None, f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
    except Exception as e:
        logger.error(f"Error downloading from HTTP {url}: {e}")
        return None, f"HTTP download error: {str(e)}"


def stream_resource(url: str):
    """
    Open resource for streaming from any supported backend.

    Parameters
    ----------
    url : str
        Resource URL

    Returns
    -------
    file-like object
        Opened file handle for streaming

    Raises
    ------
    ValueError
        If URL scheme is not supported
    Exception
        If opening stream fails
    """
    if is_pelican_url(url):
        return stream_from_pelican(url)
    else:
        raise ValueError(f"Streaming not yet supported for URL scheme: {url}")


def stream_from_pelican(url: str):
    """
    Open Pelican file for streaming.

    Parameters
    ----------
    url : str
        Pelican URL

    Returns
    -------
    file-like object
        Opened file handle
    """
    pelican_repo = get_pelican_repo_for_url(url)

    # Extract path from URL
    path = "/" + url.replace("pelican://", "").split("/", 1)[1]

    logger.info(f"Opening Pelican stream: {url} (path: {path})")
    return pelican_repo.open_file(path, mode="rb")
