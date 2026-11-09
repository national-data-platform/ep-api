# api/services/stac_services/collection_summary.py
"""
Summarise a STAC collection that a dataset's resource points to (issue #405).

A ``collection.json`` link means little to a user: it is raw JSON, often with
thousands of item paths, and browser viewers cannot read it when the server
sends no CORS headers. The Endpoint reads it instead and returns what a page
needs: extent, counts, summaries, and the list of items, each of which can be
opened to get its download links.

The Endpoint only ever fetches the URL of a resource of a public dataset in a
catalog it uses, or an item that collection links to; never a URL a caller
passes in. Fetches are http(s) only, refuse loopback, link-local, multicast
and reserved addresses (cloud metadata services among them), follow at most
a few redirects under the same rules, stop after ``STAC_MAX_BYTES`` and
``STAC_FETCH_TIMEOUT_SECONDS``, and are cached for ``STAC_CACHE_SECONDS``.
"""

import ipaddress
import json
import socket
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from fastapi import HTTPException

from api.config.catalog_settings import catalog_settings
from api.config.ckan_settings import ckan_settings
from api.config.stac_settings import stac_settings

MAX_REDIRECTS = 3
MAX_ITEMS = 10000
MAX_SUMMARY_VALUES = 200
CACHE_ENTRIES = 64

_lock = threading.Lock()
_cache: Dict[str, Any] = {}


class StacFetchError(Exception):
    """A STAC document could not be read; the message says why."""


class NotJsonError(StacFetchError):
    """The document was read but is not JSON, so it cannot be STAC."""


def _check_address(url: str) -> None:
    """Refuse URLs that are not http(s) or resolve to internal addresses."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise StacFetchError("only http and https URLs can be read")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or None)
    except socket.gaierror as exc:
        raise StacFetchError(f"{parsed.hostname} could not be resolved") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0].split("%", 1)[0])
        if (
            address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_unspecified
            or address.is_reserved
        ):
            raise StacFetchError(f"{parsed.hostname} resolves to {address}")


def _download(url: str) -> Any:
    """Fetch a JSON document under the limits above."""
    for _ in range(MAX_REDIRECTS + 1):
        _check_address(url)
        try:
            response = requests.get(
                url,
                timeout=stac_settings.stac_fetch_timeout_seconds,
                allow_redirects=False,
                stream=True,
                headers={"Accept": "application/json"},
            )
        except requests.RequestException as exc:
            raise StacFetchError(f"{url} could not be read: {exc}") from exc
        with response:
            if response.is_redirect:
                url = urljoin(url, response.headers.get("Location", ""))
                continue
            if response.status_code != 200:
                raise StacFetchError(f"{url} answered HTTP {response.status_code}")
            body = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                body.extend(chunk)
                if len(body) > stac_settings.stac_max_bytes:
                    raise StacFetchError(
                        f"{url} is larger than {stac_settings.stac_max_bytes} bytes"
                    )
        try:
            return json.loads(bytes(body))
        except ValueError as exc:
            raise NotJsonError(f"{url} is not JSON") from exc
    raise StacFetchError(f"{url} redirects too many times")


def fetch_json(url: str) -> Any:
    """Return the JSON document at ``url``, from the cache while it is fresh."""
    now = time.monotonic()
    with _lock:
        cached = _cache.get(url)
        if cached and cached[0] > now:
            return cached[1]
    document = _download(url)
    with _lock:
        if len(_cache) >= CACHE_ENTRIES:
            _cache.pop(min(_cache, key=lambda key: _cache[key][0]))
        _cache[url] = (now + stac_settings.stac_cache_seconds, document)
    return document


def clear_cache() -> None:
    """Forget every cached document (used by tests)."""
    with _lock:
        _cache.clear()


def is_collection(document: Any) -> bool:
    """True for a STAC collection document."""
    return (
        isinstance(document, dict)
        and document.get("type") == "Collection"
        and "stac_version" in document
    )


def _bbox(extent: Any) -> Optional[List[float]]:
    try:
        box = extent["spatial"]["bbox"][0]
    except (KeyError, IndexError, TypeError):
        return None
    if (
        isinstance(box, list)
        and len(box) in (4, 6)
        and all(isinstance(v, (int, float)) for v in box)
    ):
        return box
    return None


def _interval(extent: Any) -> Optional[List[Optional[str]]]:
    try:
        interval = extent["temporal"]["interval"][0]
    except (KeyError, IndexError, TypeError):
        return None
    if isinstance(interval, list) and len(interval) == 2:
        return [v if isinstance(v, str) else None for v in interval]
    return None


def _summaries(summaries: Any) -> List[Dict[str, Any]]:
    """Each summary as a name with values (or a range), lists cut short."""
    result = []
    if not isinstance(summaries, dict):
        return result
    for name, value in summaries.items():
        if isinstance(value, list):
            shown = [v for v in value if isinstance(v, (str, int, float))]
            result.append(
                {
                    "name": name,
                    "values": shown[:MAX_SUMMARY_VALUES],
                    "count": len(value),
                }
            )
        elif isinstance(value, dict) and ("minimum" in value or "maximum" in value):
            result.append(
                {
                    "name": name,
                    "minimum": value.get("minimum"),
                    "maximum": value.get("maximum"),
                }
            )
        elif isinstance(value, (str, int, float)):
            result.append({"name": name, "values": [value], "count": 1})
    return result


def _item_links(collection: Dict[str, Any], url: str) -> List[Dict[str, str]]:
    items = []
    for link in collection.get("links") or []:
        if not isinstance(link, dict) or link.get("rel") != "item":
            continue
        href = link.get("href")
        if not isinstance(href, str) or not href:
            continue
        absolute = urljoin(url, href)
        name = link.get("title") or absolute.rstrip("/").rsplit("/", 1)[-1]
        if name.endswith(".json"):
            name = name[: -len(".json")]
        items.append({"id": name, "href": absolute})
    return items


def summarize_collection(collection: Dict[str, Any], url: str) -> Dict[str, Any]:
    """The parts of a collection a page shows, with item links made absolute."""
    items = _item_links(collection, url)
    extent = collection.get("extent")
    keywords = collection.get("keywords")
    return {
        "url": url,
        "stac_version": collection.get("stac_version"),
        "id": collection.get("id"),
        "title": collection.get("title"),
        "description": collection.get("description"),
        "license": collection.get("license"),
        "keywords": keywords if isinstance(keywords, list) else [],
        "bbox": _bbox(extent),
        "interval": _interval(extent),
        "summaries": _summaries(collection.get("summaries")),
        "item_count": len(items),
        "items": items[:MAX_ITEMS],
    }


def summarize_item(item: Dict[str, Any], url: str) -> Dict[str, Any]:
    """An item's period, scalar properties and assets with absolute links."""
    properties = (
        item.get("properties") if isinstance(item.get("properties"), dict) else {}
    )
    shown = {
        key: value
        for key, value in properties.items()
        if isinstance(value, (str, int, float, bool))
        or (
            isinstance(value, list)
            and len(value) <= 50
            and all(isinstance(v, (str, int, float)) for v in value)
        )
    }
    assets = []
    for key, asset in (item.get("assets") or {}).items():
        if not isinstance(asset, dict) or not isinstance(asset.get("href"), str):
            continue
        assets.append(
            {
                "key": key,
                "title": asset.get("title") or key,
                "href": urljoin(url, asset["href"]),
                "type": asset.get("type"),
                "roles": (
                    asset.get("roles") if isinstance(asset.get("roles"), list) else []
                ),
            }
        )
    return {
        "url": url,
        "id": item.get("id"),
        "bbox": item.get("bbox") if isinstance(item.get("bbox"), list) else None,
        "properties": shown,
        "assets": assets,
    }


def _resource_url(server: str, dataset_id: str, resource_id: str) -> str:
    """The URL of a resource of a public dataset in the chosen catalog."""
    if server == "local":
        if not ckan_settings.ckan_local_enabled:
            raise HTTPException(
                status_code=400, detail="This Endpoint has no local catalog."
            )
        repository = catalog_settings.local_catalog
    elif server == "global":
        repository = catalog_settings.global_catalog
    else:
        raise HTTPException(
            status_code=400, detail="server must be 'local' or 'global'."
        )

    try:
        dataset = repository.package_show(id=dataset_id)
    except Exception:
        dataset = None
    if not isinstance(dataset, dict) or dataset.get("private"):
        raise HTTPException(status_code=404, detail="Dataset not found.")
    for resource in dataset.get("resources") or []:
        if resource.get("id") == resource_id and resource.get("url"):
            return resource["url"]
    raise HTTPException(status_code=404, detail="Resource not found in this dataset.")


def _check_enabled() -> None:
    if not stac_settings.stac_summary_enabled:
        raise HTTPException(
            status_code=404, detail="STAC summaries are turned off on this Endpoint."
        )


def _collection(server: str, dataset_id: str, resource_id: str):
    url = _resource_url(server, dataset_id, resource_id)
    try:
        document = fetch_json(url)
    except NotJsonError:
        document = None
    except StacFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not is_collection(document):
        raise HTTPException(
            status_code=422, detail="This resource is not a STAC collection."
        )
    return document, url


def get_collection_summary(
    server: str, dataset_id: str, resource_id: str
) -> Dict[str, Any]:
    """Summary of the STAC collection a dataset's resource points to."""
    _check_enabled()
    document, url = _collection(server, dataset_id, resource_id)
    return summarize_collection(document, url)


def get_item_summary(
    server: str, dataset_id: str, resource_id: str, href: str
) -> Dict[str, Any]:
    """Summary of one item of that collection; ``href`` must be one of its items."""
    _check_enabled()
    document, url = _collection(server, dataset_id, resource_id)
    if href not in {item["href"] for item in _item_links(document, url)}:
        raise HTTPException(
            status_code=404, detail="That is not an item of this collection."
        )
    try:
        item = fetch_json(href)
    except StacFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not isinstance(item, dict) or item.get("type") != "Feature":
        raise HTTPException(status_code=422, detail="That item is not a STAC item.")
    return summarize_item(item, href)
