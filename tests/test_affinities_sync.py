"""
Affinities follows the catalog (issues #279 and #280).

Registration in Affinities happened once, from two of the five registration
routes, and nothing afterwards touched it: renaming a dataset left the old
title in Affinities, deleting it left the record, its relationship and its
triple behind, and Kafka, S3 and URL datasets never reached Affinities.

Now every create, update and delete route calls
``api.services.affinities_services.sync``:

- after a create or an update, the record is replaced with the dataset's
  current title and metadata, or registered (and its UUID stored on the
  dataset) when it has none or Affinities no longer has it;
- after a delete, the record is deleted, and Affinities removes its
  relationship and triple with it. For a service, the triple it was
  registered with is deleted as well.

A stand-in Affinities on localhost keeps its records in memory, so the
tests read what Affinities ends up holding, not which calls were made.
"""

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.delete_routes import router as delete_router
from api.routes.register_routes import router as register_router
from api.routes.update_routes import router as update_router
from api.services.affinities_services.affinities_client import AffinitiesClient
from api.services.affinities_services.sync import (
    fetch_dataset,
    forget_in_affinities,
    sync_with_affinities,
)
from api.services.auth_services import ep_editor_gate

EP_UUID = "550e8400-e29b-41d4-a716-446655440000"
SETTINGS = "api.services.affinities_services.affinities_client.affinities_settings"


# ------------------------------------------------------------ Affinities


@pytest.fixture
def affinities():
    """An in-memory Affinities with the routes the Endpoint uses."""
    store = {"datasets": {}, "services": {}, "affinities": {}, "links": []}

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body=None):
            data = json.dumps(body).encode() if body is not None else b""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length)) if length else {}

        def _parts(self):
            return urlparse(self.path).path.strip("/").split("/")

        def do_POST(self):  # noqa: N802
            kind, body = self._parts()[0], self._body()
            if kind in ("datasets", "services"):
                uid = str(uuid.uuid4())
                store[kind][uid] = body
                self._send(201, {"uid": uid, **body})
            elif kind.endswith("-endpoints"):
                store["links"].append(body)
                self._send(201, body)
            elif kind == "affinities":
                uid = str(uuid.uuid4())
                store["affinities"][uid] = {
                    "triple_uid": uid,
                    "dataset_uid": body.get("dataset_uid"),
                    "service_uids": body.get("service_uids"),
                    "endpoint_uids": body.get("endpoint_uids"),
                }
                self._send(201, store["affinities"][uid])
            else:
                self._send(404, {"detail": "not found"})

        def do_PUT(self):  # noqa: N802
            kind, uid = self._parts()
            if uid not in store.get(kind, {}):
                return self._send(404, {"detail": "not found"})
            store[kind][uid].update(self._body())
            self._send(200, {"uid": uid, **store[kind][uid]})

        def do_DELETE(self):  # noqa: N802
            kind, uid = self._parts()
            if uid not in store.get(kind, {}):
                return self._send(404, {"detail": "not found"})
            del store[kind][uid]
            # The cascades of Affinities' foreign keys.
            key = {"datasets": "dataset_uid", "services": "service_uid"}.get(kind)
            if key:
                store["links"] = [
                    link for link in store["links"] if link.get(key) != uid
                ]
            if kind == "datasets":
                store["affinities"] = {
                    t: v
                    for t, v in store["affinities"].items()
                    if v["dataset_uid"] != uid
                }
            self._send(204)

        def do_GET(self):  # noqa: N802
            url = urlparse(self.path)
            if url.path == "/affinities":
                query = parse_qs(url.query)
                skip = int(query.get("skip", ["0"])[0])
                limit = int(query.get("limit", ["100"])[0])
                triples = list(store["affinities"].values())[skip : skip + limit]
                return self._send(200, triples)
            self._send(404, {"detail": "not found"})

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"

    with patch(SETTINGS) as settings:
        settings.url = url
        settings.ep_uuid = EP_UUID
        settings.timeout = 5
        settings.is_configured = True
        yield store

    server.shutdown()


# --------------------------------------------------------------- catalog


class Catalog:
    """An in-memory catalog with the calls the sync makes."""

    def __init__(self):
        self.datasets = {}

    def add(self, name, organization="org-a", **fields):
        dataset = {
            "id": f"id-{name}",
            "name": name,
            "title": fields.pop("title", name.title()),
            "notes": fields.pop("notes", None),
            "organization": {"name": organization},
            "owner_org": f"org-id-{organization}",
            "tags": [{"name": t} for t in fields.pop("tags", [])],
            "extras": [{"key": k, "value": v} for k, v in fields.items()],
            "resources": [],
        }
        self.datasets[dataset["id"]] = dataset
        return dataset

    def organization_show(self, id):
        return {"id": id, "name": id.removeprefix("org-id-")}

    def package_show(self, id):
        for dataset in self.datasets.values():
            if id in (dataset["id"], dataset["name"]):
                return json.loads(json.dumps(dataset))
        raise Exception("Not found")

    def package_update(self, **dataset):
        self.datasets[dataset["id"]] = dataset
        return dataset

    def extra(self, dataset_id, key):
        for item in self.datasets[dataset_id]["extras"]:
            if item["key"] == key:
                return item["value"]
        return None


@pytest.fixture
def catalog():
    return Catalog()


# ------------------------------------------------------- create / update


@pytest.mark.asyncio
async def test_a_dataset_without_a_record_is_registered(affinities, catalog):
    catalog.add("kafka-topic", title="Kafka topic", tags=["stream"])

    await sync_with_affinities("id-kafka-topic", repository=catalog)

    uid = catalog.extra("id-kafka-topic", "ndp_affinity_uuid")
    assert uid in affinities["datasets"]
    record = affinities["datasets"][uid]
    assert record["title"] == "Kafka topic"
    assert record["metadata"]["owner_org"] == "org-a"
    assert record["metadata"]["tags"] == ["stream"]
    assert record["metadata"]["local_id"] == "id-kafka-topic"
    # Linked to the Endpoint, with its triple.
    assert affinities["links"][0]["dataset_uid"] == uid
    assert [t["dataset_uid"] for t in affinities["affinities"].values()] == [uid]


@pytest.mark.asyncio
async def test_an_update_replaces_the_record(affinities, catalog):
    catalog.add("ds", title="Old title", notes="old notes")
    await sync_with_affinities("id-ds", repository=catalog)
    uid = catalog.extra("id-ds", "ndp_affinity_uuid")

    catalog.datasets["id-ds"]["title"] = "New title"
    catalog.datasets["id-ds"]["notes"] = "new notes"
    await sync_with_affinities("id-ds", repository=catalog)

    assert list(affinities["datasets"]) == [uid]
    assert affinities["datasets"][uid]["title"] == "New title"
    assert affinities["datasets"][uid]["metadata"]["notes"] == "new notes"
    # Still one relationship and one triple: nothing registered twice.
    assert len(affinities["links"]) == 1
    assert len(affinities["affinities"]) == 1


@pytest.mark.asyncio
async def test_a_record_gone_from_affinities_is_registered_again(affinities, catalog):
    catalog.add("ds", ndp_affinity_uuid=str(uuid.uuid4()))

    await sync_with_affinities("id-ds", repository=catalog)

    uid = catalog.extra("id-ds", "ndp_affinity_uuid")
    assert list(affinities["datasets"]) == [uid]


@pytest.mark.asyncio
async def test_a_service_is_updated_as_a_service(affinities, catalog):
    catalog.add(
        "svc",
        organization="services",
        title="Service",
        service_type="API",
        service_url="https://svc.example/api",
        documentation_url="https://svc.example/docs",
    )
    await sync_with_affinities("id-svc", repository=catalog)
    uid = catalog.extra("id-svc", "ndp_affinity_uuid")
    assert uid in affinities["services"] and not affinities["datasets"]

    catalog.datasets["id-svc"]["title"] = "Renamed service"
    await sync_with_affinities("id-svc", repository=catalog)

    record = affinities["services"][uid]
    assert record["metadata"]["service_title"] == "Renamed service"
    assert record["type"] == "API"
    assert record["openapi_url"] == "https://svc.example/docs"


@pytest.mark.asyncio
async def test_a_mongodb_service_is_still_a_service(affinities, catalog):
    # The MongoDB catalog returns owner_org (an id) and no organization:
    # the name is read from the catalog to tell a service from a dataset.
    service = catalog.add("svc", organization="services", service_type="API")
    del service["organization"]
    dataset = catalog.add("ds", organization="org-a")
    del dataset["organization"]

    await sync_with_affinities("id-svc", repository=catalog)
    await sync_with_affinities("id-ds", repository=catalog)

    assert catalog.extra("id-svc", "ndp_affinity_uuid") in affinities["services"]
    uid = catalog.extra("id-ds", "ndp_affinity_uuid")
    assert affinities["datasets"][uid]["metadata"]["owner_org"] == "org-a"

    await forget_in_affinities(fetch_dataset("id-svc", repository=catalog))
    assert affinities["services"] == {}


@pytest.mark.asyncio
async def test_affinities_off_does_nothing(catalog):
    catalog.add("ds")
    with patch(SETTINGS) as settings:
        settings.is_configured = False
        await sync_with_affinities("id-ds", repository=catalog)

    assert catalog.extra("id-ds", "ndp_affinity_uuid") is None


@pytest.mark.asyncio
async def test_affinities_down_does_not_fail(catalog):
    catalog.add("ds")
    with patch(SETTINGS) as settings:
        settings.url = "http://127.0.0.1:9"
        settings.ep_uuid = EP_UUID
        settings.timeout = 2
        settings.is_configured = True
        await sync_with_affinities("id-ds", repository=catalog)
        await forget_in_affinities(
            catalog.add("other", ndp_affinity_uuid=str(uuid.uuid4()))
        )

    assert catalog.extra("id-ds", "ndp_affinity_uuid") is None


# ---------------------------------------------------------------- delete


@pytest.mark.asyncio
async def test_a_deleted_dataset_leaves_nothing_in_affinities(affinities, catalog):
    catalog.add("ds")
    await sync_with_affinities("id-ds", repository=catalog)

    await forget_in_affinities(fetch_dataset("id-ds", repository=catalog))

    assert affinities["datasets"] == {}
    assert affinities["links"] == []
    assert affinities["affinities"] == {}


@pytest.mark.asyncio
async def test_a_deleted_service_leaves_nothing_in_affinities(affinities, catalog):
    catalog.add("svc", organization="services", service_type="API")
    await sync_with_affinities("id-svc", repository=catalog)
    # Another Endpoint's triple naming two services is not ours to remove.
    other = str(uuid.uuid4())
    affinities["affinities"][other] = {
        "triple_uid": other,
        "dataset_uid": None,
        "service_uids": [catalog.extra("id-svc", "ndp_affinity_uuid"), "x"],
    }

    await forget_in_affinities(fetch_dataset("id-svc", repository=catalog))

    assert affinities["services"] == {}
    assert affinities["links"] == []
    assert list(affinities["affinities"]) == [other]


@pytest.mark.asyncio
async def test_deleting_a_record_affinities_no_longer_has_is_fine(affinities, catalog):
    dataset = catalog.add("ds", ndp_affinity_uuid=str(uuid.uuid4()))

    assert (
        await AffinitiesClient().delete_dataset(
            catalog.extra(dataset["id"], "ndp_affinity_uuid")
        )
        == AffinitiesClient.OK
    )


@pytest.mark.asyncio
async def test_an_unregistered_dataset_is_not_looked_for(affinities, catalog):
    await forget_in_affinities(catalog.add("ds"))
    await forget_in_affinities(None)

    assert affinities["datasets"] == {}


# ---------------------------------------------------------------- routes


@pytest.fixture
def client():
    # The routes themselves, not api.main: it mounts the write routes only
    # when a local catalog is configured, which CI has not.
    app = FastAPI()
    for router in (register_router, update_router, delete_router):
        app.include_router(router)
    app.dependency_overrides[ep_editor_gate] = lambda: {
        "username": "tester",
        "roles": ["admin"],
    }
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def synced():
    """Record each route's call into the sync instead of making it."""
    calls = []

    async def sync(dataset_id, repository=None, ckan_instance=None):
        calls.append(("sync", dataset_id))

    async def forget(dataset):
        calls.append(("forget", dataset and dataset["id"]))

    modules = {
        "sync_with_affinities": [
            "api.routes.register_routes.post_kafka",
            "api.routes.register_routes.post_s3",
            "api.routes.register_routes.post_url",
            "api.routes.register_routes.post_general_dataset",
            "api.routes.register_routes.post_service",
            "api.routes.update_routes.put_general_dataset",
            "api.routes.update_routes.patch_general_dataset",
            "api.routes.update_routes.put_kafka",
            "api.routes.update_routes.patch_kafka",
            "api.routes.update_routes.put_s3",
            "api.routes.update_routes.patch_s3",
            "api.routes.update_routes.put_url",
            "api.routes.update_routes.patch_url",
            "api.routes.update_routes.put_service",
            "api.routes.update_routes.patch_service",
        ],
        "forget_in_affinities": [
            "api.routes.delete_routes.delete_dataset",
            "api.routes.delete_routes.delete_organization_route",
        ],
    }
    patches = [
        patch(f"{module}.{name}", sync if name.startswith("sync") else forget)
        for name, targets in modules.items()
        for module in targets
    ]
    for p in patches:
        p.start()
    yield calls
    for p in patches:
        p.stop()


@pytest.mark.parametrize(
    "path, service, body",
    [
        (
            "/kafka",
            "api.routes.register_routes.post_kafka.kafka_services.add_kafka",
            {
                "dataset_name": "k",
                "dataset_title": "K",
                "owner_org": "org-a",
                "kafka_topic": "t",
                "kafka_host": "h",
                "kafka_port": "9092",
            },
        ),
        (
            "/s3",
            "api.routes.register_routes.post_s3.add_s3",
            {
                "resource_name": "s",
                "resource_title": "S",
                "owner_org": "org-a",
                "resource_s3": "s3://bucket/key",
            },
        ),
        (
            "/url",
            "api.routes.register_routes.post_url.add_url",
            {
                "resource_name": "u",
                "resource_title": "U",
                "owner_org": "org-a",
                "resource_url": "https://example.org/data.csv",
            },
        ),
    ],
)
def test_kafka_s3_and_url_datasets_reach_affinities(
    client, synced, path, service, body
):
    with patch(service, return_value="new-id"):
        response = client.post(path, json=body)

    assert response.status_code in (200, 201), response.text
    assert synced == [("sync", "new-id")]


@pytest.mark.parametrize(
    "method, path, service, body",
    [
        (
            "put",
            "/dataset/id-1",
            "put_general_dataset.update_general_dataset",
            {"name": "n", "title": "T", "owner_org": "org-a"},
        ),
        (
            "patch",
            "/dataset/id-1",
            "patch_general_dataset.patch_general_dataset",
            {"title": "T"},
        ),
        (
            "patch",
            "/kafka/id-1",
            "patch_kafka.kafka_services.patch_kafka",
            {"dataset_title": "T"},
        ),
        ("patch", "/s3/id-1", "patch_s3.patch_s3", {"resource_title": "T"}),
        ("patch", "/url/id-1", "patch_url.patch_url", {"resource_title": "T"}),
        (
            "patch",
            "/services/id-1",
            "patch_service.patch_service",
            {"service_title": "T"},
        ),
    ],
)
def test_updates_reach_affinities(client, synced, method, path, service, body):
    target = f"api.routes.update_routes.{service}"
    # patch_url answers with the updated resource; the others with its id.
    result = {"id": "id-1"} if service.startswith("patch_url") else "id-1"
    with patch(target, return_value=result):
        response = getattr(client, method)(path, json=body)

    assert response.status_code == 200, response.text
    assert synced == [("sync", "id-1")]


def test_a_failed_update_does_not_reach_affinities(client, synced):
    target = "api.routes.update_routes.patch_general_dataset.patch_general_dataset"
    with patch(target, return_value=None):
        response = client.patch("/dataset/id-1", json={"title": "T"})

    assert response.status_code == 404
    assert synced == []


def test_a_delete_reads_the_dataset_first_and_forgets_it(client, synced, catalog):
    catalog.add("ds")
    with (
        patch(
            "api.routes.delete_routes.delete_dataset.fetch_dataset",
            side_effect=lambda dataset_id, repository=None: catalog.package_show(
                dataset_id
            ),
        ),
        patch(
            "api.routes.delete_routes.delete_dataset.dataset_services.delete_dataset"
        ) as delete,
    ):
        by_id = client.delete("/resource", params={"resource_id": "id-ds"})
        by_name = client.delete("/resource/ds")

    assert by_id.status_code == 200 and by_name.status_code == 200
    assert delete.call_count == 2
    assert synced == [("forget", "id-ds"), ("forget", "id-ds")]


def test_an_organization_cascade_forgets_its_datasets(client, synced, catalog):
    deleted = [catalog.add("a"), catalog.add("b")]
    with patch(
        "api.routes.delete_routes.delete_organization_route."
        "organization_services.delete_organization",
        return_value=deleted,
    ):
        response = client.delete("/organization/org-a")

    assert response.status_code == 200, response.text
    assert synced == [("forget", "id-a"), ("forget", "id-b")]


def test_delete_organization_returns_what_it_deleted(catalog):
    from api.services.organization_services.delete_organization import (
        delete_organization,
    )

    repo = MagicMock()
    repo.organization_show.return_value = {"id": "org-id"}
    repo.package_search.return_value = {"results": [{"id": "a"}, {"id": "b"}]}

    assert delete_organization("org-a", repository=repo) == [
        {"id": "a"},
        {"id": "b"},
    ]
