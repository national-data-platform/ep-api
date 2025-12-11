# api/services/pelican_services/browse_federation.py
"""
Service for browsing Pelican federation namespaces.
"""

from typing import Dict, List, Any
from api.repositories.pelican_repository import PelicanRepository
import logging

logger = logging.getLogger(__name__)


def browse_namespace(
    pelican_repo: PelicanRepository,
    path: str,
    detail: bool = False
) -> Dict[str, Any]:
    """
    Browse files in a Pelican federation namespace.

    Parameters
    ----------
    pelican_repo : PelicanRepository
        Initialized Pelican repository
    path : str
        Namespace path to browse
    detail : bool
        If True, return detailed file information

    Returns
    -------
    dict
        Response with 'path', 'files', and 'count'
    """
    try:
        files = pelican_repo.list_files(path, detail=detail)

        return {
            "success": True,
            "path": path,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        logger.error(f"Error browsing namespace {path}: {e}")
        return {
            "success": False,
            "path": path,
            "error": str(e),
            "files": [],
            "count": 0
        }


def get_file_info(
    pelican_repo: PelicanRepository,
    path: str
) -> Dict[str, Any]:
    """
    Get metadata for a specific file without downloading.

    Parameters
    ----------
    pelican_repo : PelicanRepository
        Initialized Pelican repository
    path : str
        File path

    Returns
    -------
    dict
        File metadata
    """
    try:
        info = pelican_repo.file_info(path)
        return {
            "success": True,
            "file": info
        }
    except Exception as e:
        logger.error(f"Error getting file info for {path}: {e}")
        return {
            "success": False,
            "error": str(e)
        }
