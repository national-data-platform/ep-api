# api/services/pelican_services/read_file.py
"""
Service for reading Pelican objects into the response body.
"""

import base64
import logging
from typing import Any, Dict

from api.repositories.pelican_repository import PelicanRepository

logger = logging.getLogger(__name__)


def read_object(
    pelican_repo: PelicanRepository, path: str, max_bytes: int
) -> Dict[str, Any]:
    """
    Read the contents of a Pelican object and return them inline.

    Unlike :func:`api.services.pelican_services.download_file.download_file`,
    which hands the caller a file to save, this returns the contents in the
    response body so they can be fed straight into the caller's own code
    without a temporary file.

    The size cap is enforced *while* reading rather than after: an object
    larger than the cap must not be pulled into the endpoint's memory just
    to be rejected, which is why this reads through an open handle instead
    of calling ``read_file``.

    Parameters
    ----------
    pelican_repo : PelicanRepository
        Initialized Pelican repository
    path : str
        Path of the object to read
    max_bytes : int
        Largest object this endpoint will return inline

    Returns
    -------
    dict
        On success, ``path``, ``size``, ``encoding`` and ``content``.
        On failure, ``error`` plus a ``reason`` of ``not_found``,
        ``too_large`` or ``unavailable`` for the caller to map to a
        status code.
    """
    try:
        with pelican_repo.open_file(path, mode="rb") as handle:
            # One byte past the cap, so an oversized object is detected
            # without being read in full.
            payload = handle.read(max_bytes + 1)
    except FileNotFoundError as exc:
        logger.info(f"Pelican object not found: {path}")
        return {
            "success": False,
            "path": path,
            "error": f"Object not found in the federation: {str(exc) or path}",
            "reason": "not_found",
        }
    except Exception as exc:
        logger.error(f"Error reading Pelican object {path}: {exc}")
        return {
            "success": False,
            "path": path,
            "error": f"{type(exc).__name__}: {exc}",
            "reason": "unavailable",
        }

    if len(payload) > max_bytes:
        return {
            "success": False,
            "path": path,
            "error": (
                f"Object is larger than the {max_bytes} byte inline read "
                "limit. Use /pelican/download to retrieve it as a file."
            ),
            "reason": "too_large",
        }

    # Text is returned as text so a caller can use it directly; anything
    # that is not valid UTF-8 is base64-encoded rather than rejected, and
    # says so, because Pelican namespaces hold binary payloads too.
    try:
        content = payload.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        content = base64.b64encode(payload).decode("ascii")
        encoding = "base64"

    logger.info(f"Read {len(payload)} bytes from Pelican object {path}")
    return {
        "success": True,
        "path": path,
        "size": len(payload),
        "encoding": encoding,
        "content": content,
    }
