"""Summaries of STAC collection resources (issue #405).

A stand-in file server serves a collection like the GLSR one; the catalog is
a stand-in whose dataset has that collection as a resource.
"""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.config.stac_settings import stac_settings
from api.main import app
from api.services.stac_services import collection_summary as stac

COLLECTION = {
    "stac_version": "1.0.0",
    "type": "Collection",
    "id": "macav2-gslbip",
    "title": "MACAv2 Statistically Downscaled CMIP6 — GSLBIP",
    "description": "Surface meteorological data for the Great Salt Lake Basin.",
    "license": "other",
    "extent": {
        "spatial": {"bbox": [[-115.1, 36.025, -108.01667, 42.983334]]},
        "temporal": {"interval": [["1979-01-01T00:00:00Z", "2099-12-31T23:59:59Z"]]},
    },
    "summaries": {
        "model": ["ACCESS-CM2", "MIROC6"],
        "scenario": ["ssp126", "ssp370"],
        "file_count": 2,
    },
    "links": [
        {"rel": "self", "href": "collection.json"},
        {"rel": "item", "href": "items/a_ACCESS-CM2_ssp126_1979-1988.json"},
        {"rel": "item", "href": "items/b_MIROC6_ssp370_2090-2099.json"},
    ],
}
ITEM = {
    "stac_version": "1.0.0",
    "type": "Feature",
    "id": "a_ACCESS-CM2_ssp126_1979-1988",
    "bbox": [-115.1, 36.025, -108.01667, 42.983334],
    "properties": {
        "datetime": None,
        "start_datetime": "1979-01-01T00:00:00Z",
        "end_datetime": "1988-12-31T23:59:59Z",
        "model": "ACCESS-CM2",
        "variables": ["pr", "tasmax"],
    },
    "assets": {
        "data": {
            "href": "../a_ACCESS-CM2_ssp126_1979-1988.nc",
            "type": "application/x-netcdf",
            "roles": ["data"],
        }
    },
}


@pytest.fixture
def files():
    """A file server: /stac/collection.json, its items, and a non-STAC file."""
    served = {
        "/stac/collection.json": COLLECTION,
        "/stac/items/a_ACCESS-CM2_ssp126_1979-1988.json": ITEM,
        "/stac/items/b_MIROC6_ssp370_2090-2099.json": dict(ITEM, id="b"),
        "/plain.json": {"hello": "world"},
    }
    state = {"requests": []}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["requests"].append(self.path)
            if self.path == "/big.json":
                body = b"[" + b"0," * (stac_settings.stac_max_bytes) + b"0]"
            elif self.path == "/to-metadata":
                self.send_response(302)
                self.send_header("Location", "http://169.254.169.254/latest/")
                self.end_headers()
                return
            elif self.path == "/page.html":
                body = b"<html><body>Index of /files/</body></html>"
            elif self.path in served:
                body = json.dumps(served[self.path]).encode()
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state["base"] = f"http://127.0.0.1:{server.server_address[1]}"
    stac.clear_cache()
    yield state
    server.shutdown()
    stac.clear_cache()


@pytest.fixture
def allow_local_server():
    """The stand-in server is on loopback, which real fetches refuse."""
    real = stac._check_address

    def check(url):
        if url.startswith("http://127.0.0.1:"):
            return
        real(url)

    with patch.object(stac, "_check_address", side_effect=check):
        yield


def _catalog_with(url, private=False):
    repo = MagicMock()
    repo.package_show.return_value = {
        "id": "ds-1",
        "name": "macav2-gslbip-stac",
        "private": private,
        "resources": [
            {"id": "res-stac", "url": url, "format": "JSON"},
            {"id": "res-other", "url": "https://example.org/files/"},
        ],
    }
    catalog = MagicMock()
    catalog.global_catalog = repo
    catalog.local_catalog = repo
    return patch.object(stac, "catalog_settings", catalog)


def _get(path, **params):
    return TestClient(app).get(path, params=params)


def _collection(**params):
    return _get(
        "/stac/collection",
        dataset_id="macav2-gslbip-stac",
        resource_id="res-stac",
        **params,
    )


def test_the_collection_is_summarised(files, allow_local_server):
    url = files["base"] + "/stac/collection.json"
    with _catalog_with(url):
        response = _collection()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == COLLECTION["title"]
    assert body["bbox"] == [-115.1, 36.025, -108.01667, 42.983334]
    assert body["interval"] == ["1979-01-01T00:00:00Z", "2099-12-31T23:59:59Z"]
    assert {"name": "model", "values": ["ACCESS-CM2", "MIROC6"], "count": 2} in body[
        "summaries"
    ]
    assert {"name": "file_count", "values": [2], "count": 1} in body["summaries"]
    assert body["item_count"] == 2
    assert body["items"][0] == {
        "id": "a_ACCESS-CM2_ssp126_1979-1988",
        "href": files["base"] + "/stac/items/a_ACCESS-CM2_ssp126_1979-1988.json",
    }


def test_an_item_shows_its_assets_with_absolute_links(files, allow_local_server):
    url = files["base"] + "/stac/collection.json"
    href = files["base"] + "/stac/items/a_ACCESS-CM2_ssp126_1979-1988.json"
    with _catalog_with(url):
        response = _get(
            "/stac/item",
            dataset_id="macav2-gslbip-stac",
            resource_id="res-stac",
            href=href,
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["properties"]["start_datetime"] == "1979-01-01T00:00:00Z"
    assert body["properties"]["variables"] == ["pr", "tasmax"]
    assert body["assets"] == [
        {
            "key": "data",
            "title": "data",
            "href": files["base"] + "/stac/a_ACCESS-CM2_ssp126_1979-1988.nc",
            "type": "application/x-netcdf",
            "roles": ["data"],
        }
    ]


def test_an_href_that_is_not_an_item_of_the_collection_is_never_fetched(
    files, allow_local_server
):
    url = files["base"] + "/stac/collection.json"
    with _catalog_with(url):
        response = _get(
            "/stac/item",
            dataset_id="macav2-gslbip-stac",
            resource_id="res-stac",
            href=files["base"] + "/plain.json",
        )

    assert response.status_code == 404
    assert "/plain.json" not in files["requests"]


def test_the_collection_is_read_once_while_cached(files, allow_local_server):
    url = files["base"] + "/stac/collection.json"
    with _catalog_with(url):
        _collection()
        _collection()

    assert files["requests"].count("/stac/collection.json") == 1


def test_a_resource_that_is_not_stac_is_422(files, allow_local_server):
    with _catalog_with(files["base"] + "/plain.json"):
        response = _collection()

    assert response.status_code == 422


def test_a_resource_that_is_not_json_is_422(files, allow_local_server):
    with _catalog_with(files["base"] + "/page.html"):
        response = _collection()

    assert response.status_code == 422


def test_a_private_dataset_is_404(files, allow_local_server):
    with _catalog_with(files["base"] + "/stac/collection.json", private=True):
        response = _collection()

    assert response.status_code == 404
    assert files["requests"] == []


def test_an_unknown_resource_is_404(files, allow_local_server):
    with _catalog_with(files["base"] + "/stac/collection.json"):
        response = _get(
            "/stac/collection", dataset_id="macav2-gslbip-stac", resource_id="nope"
        )

    assert response.status_code == 404
    assert files["requests"] == []


def test_turned_off_it_reads_nothing(files, allow_local_server, monkeypatch):
    monkeypatch.setattr(stac_settings, "stac_summary_enabled", False)
    with _catalog_with(files["base"] + "/stac/collection.json"):
        response = _collection()

    assert response.status_code == 404
    assert files["requests"] == []


def test_a_document_over_the_size_limit_is_502(files, allow_local_server, monkeypatch):
    monkeypatch.setattr(stac_settings, "stac_max_bytes", 1000)
    with _catalog_with(files["base"] + "/big.json"):
        response = _collection()

    assert response.status_code == 502
    assert "larger than" in response.json()["detail"]


def test_a_redirect_to_an_internal_address_is_refused(files, allow_local_server):
    with _catalog_with(files["base"] + "/to-metadata"):
        response = _collection()

    assert response.status_code == 502
    assert "169.254.169.254" in response.json()["detail"]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/collection.json",
        "http://localhost/collection.json",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/collection.json",
        "http://0.0.0.0/collection.json",
        "file:///etc/passwd",
        "ftp://example.org/collection.json",
    ],
)
def test_internal_addresses_and_other_schemes_are_refused(url):
    with pytest.raises(stac.StacFetchError):
        stac._check_address(url)


def test_a_public_address_is_allowed():
    public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("155.101.6.192", 443))]
    with patch.object(stac.socket, "getaddrinfo", return_value=public):
        stac._check_address(
            "https://utah-cmip6.ndp.utah.edu/files/stac/collection.json"
        )


def test_a_private_network_address_is_allowed():
    """Endpoints on internal networks keep their files on private addresses."""
    private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.244.2.248", 80))]
    with patch.object(stac.socket, "getaddrinfo", return_value=private):
        stac._check_address("http://files.internal/collection.json")
