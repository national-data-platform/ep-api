# api/services/pelican_services/download_file.py
"""
Service for downloading files from Pelican federation.
"""

from typing import BinaryIO
from api.repositories.pelican_repository import PelicanRepository
import logging

logger = logging.getLogger(__name__)


def download_file(
    pelican_repo: PelicanRepository,
    path: str
) -> bytes:
    """
    Download file contents from Pelican federation.

    Parameters
    ----------
    pelican_repo : PelicanRepository
        Initialized Pelican repository
    path : str
        File path to download

    Returns
    -------
    bytes
        File contents

    Raises
    ------
    Exception
        If download fails
    """
    try:
        logger.info(f"Downloading file from Pelican: {path}")
        contents = pelican_repo.read_file(path)
        logger.info(f"Successfully downloaded {len(contents)} bytes from {path}")
        return contents
    except Exception as e:
        logger.error(f"Error downloading file {path}: {e}")
        raise


def stream_file(
    pelican_repo: PelicanRepository,
    path: str
):
    """
    Open file for streaming from Pelican federation.

    Parameters
    ----------
    pelican_repo : PelicanRepository
        Initialized Pelican repository
    path : str
        File path to stream

    Returns
    -------
    file-like object
        Opened file handle for streaming

    Raises
    ------
    Exception
        If opening file fails
    """
    try:
        logger.info(f"Opening file stream from Pelican: {path}")
        return pelican_repo.open_file(path, mode="rb")
    except Exception as e:
        logger.error(f"Error opening file stream {path}: {e}")
        raise
