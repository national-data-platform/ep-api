# api/repositories/pelican_repository.py
"""
Pelican federation data access repository.

This module provides access to Pelican data federations for browsing and
downloading files from distributed scientific data repositories.
"""

from typing import Dict, List, Any, Optional
from pelicanfs.core import PelicanFileSystem, PelicanMap
import logging

logger = logging.getLogger(__name__)


class PelicanRepository:
    """
    Repository for accessing Pelican data federations.

    Unlike DataCatalogRepository (which manages metadata), this repository
    handles actual file access from Pelican federations like OSDF.
    """

    def __init__(
        self,
        federation_url: str,
        direct_reads: bool = False,
        preferred_caches: Optional[List[str]] = None,
    ):
        """
        Initialize Pelican filesystem connection.

        Parameters
        ----------
        federation_url : str
            Pelican federation URL (e.g., "pelican://osg-htc.org")
        direct_reads : bool
            If True, read directly from origins bypassing caches
        preferred_caches : list, optional
            List of preferred cache URLs
        """
        self.federation_url = federation_url
        self.direct_reads = direct_reads
        self.preferred_caches = preferred_caches or []

        self._fs = None

    @property
    def fs(self) -> PelicanFileSystem:
        """Lazy-load filesystem connection."""
        if self._fs is None:
            self._fs = PelicanFileSystem(
                self.federation_url,
                direct_reads=self.direct_reads,
                preferred_caches=self.preferred_caches,
            )
        return self._fs

    def list_files(self, path: str, detail: bool = False) -> List[Dict[str, Any]]:
        """
        List files in a Pelican namespace path.

        Parameters
        ----------
        path : str
            Namespace path to list (e.g., "/ospool/uc-shared/public")
        detail : bool
            If True, return detailed file information

        Returns
        -------
        list
            List of file paths or detailed file information dicts
        """
        try:
            if detail:
                # Returns list of dicts with name, size, type, etc.
                files = self.fs.ls(path, detail=True)
                return [
                    {
                        "name": f.get("name", ""),
                        "size": f.get("size", 0),
                        "type": f.get("type", "file"),
                        "modified": f.get("mtime", None),
                    }
                    for f in files
                ]
            else:
                # Returns list of path strings
                return self.fs.ls(path, detail=False)
        except Exception as e:
            logger.error(f"Error listing files in {path}: {e}")
            raise

    def read_file(self, path: str) -> bytes:
        """
        Read file contents from Pelican federation.

        Parameters
        ----------
        path : str
            Full path to file in federation

        Returns
        -------
        bytes
            File contents
        """
        try:
            return self.fs.cat(path)
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            raise

    def file_info(self, path: str) -> Dict[str, Any]:
        """
        Get file metadata without downloading content.

        Parameters
        ----------
        path : str
            Path to file

        Returns
        -------
        dict
            File metadata (size, type, modified time, etc.)
        """
        try:
            info = self.fs.info(path)
            return {
                "name": info.get("name", ""),
                "size": info.get("size", 0),
                "type": info.get("type", "file"),
                "modified": info.get("mtime", None),
            }
        except Exception as e:
            logger.error(f"Error getting info for {path}: {e}")
            raise

    def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in the federation.

        Parameters
        ----------
        path : str
            Path to check

        Returns
        -------
        bool
            True if file exists, False otherwise
        """
        try:
            return self.fs.exists(path)
        except Exception as e:
            logger.error(f"Error checking existence of {path}: {e}")
            return False

    def open_file(self, path: str, mode: str = "rb"):
        """
        Open a file for streaming/reading.

        Parameters
        ----------
        path : str
            Path to file
        mode : str
            File open mode (default "rb" for binary read)

        Returns
        -------
        file-like object
            Opened file handle
        """
        try:
            return self.fs.open(path, mode=mode)
        except Exception as e:
            logger.error(f"Error opening file {path}: {e}")
            raise

    def check_health(self) -> bool:
        """
        Check if Pelican federation is accessible.

        Returns
        -------
        bool
            True if federation is reachable, False otherwise
        """
        try:
            # Try to list root directory
            self.fs.ls("/")
            return True
        except Exception as e:
            logger.error(f"Pelican health check failed: {e}")
            return False
