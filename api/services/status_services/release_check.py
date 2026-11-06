# api/services/status_services/release_check.py
"""
Compare the installed ep-api version with the latest published release.

Admins of an Endpoint otherwise only learn about new releases by checking
GitHub themselves (issue #395). The latest release is read from the GitHub
releases API and kept for ``RELEASE_CHECK_INTERVAL_SECONDS``, so a busy
Endpoint asks GitHub a few times a day at most; a failed lookup is kept for
a shorter time so an offline Endpoint does not retry on every request. When
the lookup fails or is turned off, the answer still carries the installed
version, with the latest one unknown.
"""

import logging
import re
import threading
import time
from typing import Any, Dict, Optional, Tuple

import requests

from api.config.swagger_settings import swagger_settings

logger = logging.getLogger(__name__)

# How long a failed lookup is remembered before GitHub is asked again.
FAILURE_RETRY_SECONDS = 900
REQUEST_TIMEOUT_SECONDS = 5

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
_RELEASE_PAGE_RE = re.compile(
    r"^(https://github\.com/[^/]+/[^/]+)/releases/tag/([^/]+)$"
)

_lock = threading.Lock()
_cache: Dict[str, Any] = {"expires": 0.0, "release": None}


def parse_version(value: Optional[str]) -> Optional[Tuple[int, int, int]]:
    """Return (major, minor, patch) for "1.2.3" or "v1.2.3", else None."""
    if not isinstance(value, str):
        return None
    match = _VERSION_RE.match(value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def changelog_url_for(release_url: Optional[str]) -> Optional[str]:
    """The CHANGELOG at a GitHub release's tag, or None for other URLs."""
    if not release_url:
        return None
    match = _RELEASE_PAGE_RE.match(release_url)
    if not match:
        return None
    repo, tag = match.groups()
    return f"{repo}/blob/{tag}/CHANGELOG.md"


def _fetch_latest_release() -> Optional[Dict[str, str]]:
    """Ask the releases API for the latest release; None when it cannot."""
    try:
        response = requests.get(
            swagger_settings.release_check_url,
            headers={"Accept": "application/vnd.github+json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.info("Latest ep-api release could not be read: %s", exc)
        return None

    tag = data.get("tag_name") if isinstance(data, dict) else None
    if parse_version(tag) is None:
        logger.info("Latest ep-api release has no usable version: %r", tag)
        return None
    return {"tag": tag, "url": data.get("html_url") or ""}


def _latest_release() -> Optional[Dict[str, str]]:
    """The latest release, from the cache while it is fresh."""
    with _lock:
        now = time.monotonic()
        if now < _cache["expires"]:
            return _cache["release"]
        release = _fetch_latest_release()
        lifetime = (
            swagger_settings.release_check_interval_seconds
            if release
            else FAILURE_RETRY_SECONDS
        )
        _cache["release"] = release
        _cache["expires"] = now + lifetime
        return release


def clear_cache() -> None:
    """Forget the cached release (used by tests)."""
    with _lock:
        _cache["expires"] = 0.0
        _cache["release"] = None


def get_version_info() -> Dict[str, Any]:
    """
    Describe the installed version and the latest published release.

    ``update_available`` is True only when both versions are known and the
    latest is newer; it is False when they are equal or the installed one is
    newer (a development build), and None when the latest is unknown.
    """
    current = swagger_settings.swagger_version
    info: Dict[str, Any] = {
        "current_version": current,
        "latest_version": None,
        "update_available": None,
        "release_url": None,
        "changelog_url": None,
        "check_enabled": swagger_settings.release_check_enabled,
    }
    if not swagger_settings.release_check_enabled:
        return info

    release = _latest_release()
    if not release:
        return info

    latest = release["tag"].lstrip("v")
    info["latest_version"] = latest
    info["release_url"] = release["url"] or None
    info["changelog_url"] = changelog_url_for(release["url"])

    current_parsed = parse_version(current)
    if current_parsed is not None:
        info["update_available"] = parse_version(latest) > current_parsed
    return info
