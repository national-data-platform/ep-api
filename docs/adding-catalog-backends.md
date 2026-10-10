# Adding a catalog backend

How the Endpoint talks to its local catalog, and what it takes to add a
backend next to CKAN and MongoDB. For where this sits in the whole system, see
[architecture/overview.md](architecture/overview.md#7-the-repository-pattern).

## Contents

1. [How catalogs are reached](#1-how-catalogs-are-reached)
2. [The interface](#2-the-interface)
3. [What the services expect from a backend](#3-what-the-services-expect-from-a-backend)
4. [Step by step](#4-step-by-step)
5. [Testing](#5-testing)
6. [Code that does not go through the repository](#6-code-that-does-not-go-through-the-repository)

---

## 1. How catalogs are reached

The Endpoint works with three catalogs. Only the **local** one has a choice of
backend:

| Catalog | Backend | Selected by |
|---|---|---|
| Local | `CKANRepository`, `MongoDBRepository`, or none | `LOCAL_CATALOG_BACKEND` = `ckan` (default), `mongodb` or `none` |
| Global (read-only) | always `CKANRepository` | `CKAN_GLOBAL_URL` |
| Pre-CKAN (staging) | always `CKANRepository` | `PRE_CKAN_*` |

```mermaid
flowchart TD
    Routes["Routes (api/routes/)"] --> Services["Services (api/services/)"]
    Services --> Factory["catalog_settings<br/>(api/config/catalog_settings.py)"]
    Factory -->|"local_catalog"| Choice{LOCAL_CATALOG_BACKEND}
    Choice -->|ckan| CKAN["CKANRepository(ckan_settings.ckan)"]
    Choice -->|mongodb| Mongo["MongoDBRepository(MONGODB_CONNECTION_STRING, MONGODB_DATABASE)"]
    Choice -->|none| None["ValueError: no local catalog"]
    Factory -->|"global_catalog"| G["CKANRepository(ckan_settings.ckan_global)"]
    Factory -->|"pre_catalog"| P["CKANRepository(ckan_settings.pre_ckan)"]
    CKAN --> Base["DataCatalogRepository<br/>(api/repositories/base_repository.py)"]
    Mongo --> Base
```

The factory is the module-level `catalog_settings` object
([`api/config/catalog_settings.py`](../api/config/catalog_settings.py)):

- `local_catalog` builds the repository for `LOCAL_CATALOG_BACKEND`
  (case-insensitive). For `none` it raises `ValueError` explaining that the
  Endpoint has no local catalog; for an unknown value it raises
  `ValueError("Unsupported catalog backend: …")`.
- `has_local_catalog` is `False` only for `none`. `api/main.py` mounts the
  catalog write routes only when it is true **and** `CKAN_LOCAL_ENABLED` is
  true; the metrics task and `/ready` also check it before asking for the
  repository.
- `global_catalog`, `pre_catalog` and `get_repository_by_name("local" |
  "global" | "pre")` complete it.

The properties build a **new repository object on every access**; a backend's
constructor therefore runs once per request that touches the catalog (the
MongoDB backend opens a `MongoClient` and checks its indexes each time). Keep
constructors cheap, or cache the client at module level.

Services receive a repository as an argument or ask `catalog_settings` for
one, e.g. `create_general_dataset(..., repository=None)` falls back to
`catalog_settings.local_catalog`.

---

## 2. The interface

`DataCatalogRepository` in
[`api/repositories/base_repository.py`](../api/repositories/base_repository.py)
is an `ABC`. A backend must implement every abstract method — a missing one
makes instantiation fail with `TypeError`:

| Method | Called with | Must return |
|---|---|---|
| `package_create(**kwargs)` | `name`, `title`, `owner_org`, and optionally `notes`, `extras`, `tags`, `groups`, `resources`, `private`, `license_id`, `version`, … | the created package, with at least `id` and `name` |
| `package_show(id)` | id **or** name | the package |
| `package_update(**kwargs)` | the full package (as returned by `package_show`, modified) | the updated package, with `id` |
| `package_patch(**kwargs)` | `id` plus the fields to change | the updated package |
| `package_delete(id)` | id or name | `None` |
| `package_search(q="*:*", fq="", rows=10, start=0, sort="score desc, metadata_modified desc", **kwargs)` | see [§3](#3-what-the-services-expect-from-a-backend) | `{"count": int, "results": [package, …]}` |
| `resource_create(**kwargs)` | `package_id`, `url`, `name`, and optionally `description`, `format`, … | the resource, with `id` |
| `resource_show(id)` | resource id | the resource |
| `resource_delete(id)` | resource id | `None` |
| `resource_patch(**kwargs)` | `id` plus any of `name`, `url`, `description`, `format` | the updated resource |
| `organization_create(**kwargs)` | `name`, `title`, `description`, and the creator hashes `ndp_user_id` and `ndp_creator_md5` as top-level keyword arguments | the organization, with `id` |
| `organization_show(id)` | id or name | the organization, with `id` and `name` |
| `organization_list(all_fields=False, **kwargs)` | `all_fields=True, include_extras=True` for `?mine=true` | a list of names, or of full organizations with `all_fields=True` |
| `organization_delete(id)` | organization id | `None` |
| `check_health()` | | `True` when the backend is reachable, `False` otherwise (must not raise) |

`resource_search(query, name, url, format, description, limit=100, offset=0)`
is **not** abstract. Its default implementation calls
`package_search(q="*:*", rows=1000)` and filters the resources in Python,
returning `{"count": n, "results": [...]}` with `dataset_id`, `dataset_name`
and `dataset_title` added to each resource. Override it when the backend can
query resources directly (`MongoDBRepository` does).

Data follows the shapes of CKAN's action API, because the services were
written against CKAN and the global and staging catalogs are CKAN:

```python
{
    "id": "uuid",
    "name": "unique-name",
    "title": "Title",
    "owner_org": "organization id",
    "notes": "description",
    "extras": [{"key": "k", "value": "v"}],
    "tags": [{"name": "tag"}],
    "groups": [{"name": "group"}],
    "private": False,
    "resources": [{"id": "uuid", "package_id": "…", "name": "…", "url": "…",
                   "format": "…", "description": "…"}],
    "metadata_created": "ISO 8601",
    "metadata_modified": "ISO 8601",
    "state": "active",
}
```

---

## 3. What the services expect from a backend

Beyond the signatures, the services rely on behaviour that CKAN has and a new
backend must reproduce.

**`package_search` arguments.** Callers pass:

- `q`: `"*:*"` for everything; a free-text string; or `field:value` parts
  joined with ` AND ` (for example `name:x AND organization:y`). `organization`
  means the owning organization by name.
- `fq`: a single `field:value` filter, e.g. `owner_org:<id>` or
  `owner_org:services` (an organization **name** in the second case — the
  metrics task counts services this way).
- `fq_list`: a list of `field:value` filters (`POST /search`); it arrives in
  `**kwargs`.
- `rows`: up to 1000, and `0` when only `count` is wanted; `start` for paging;
  `sort`.

`MongoDBRepository.package_search` is a worked example of mapping these onto a
non-Solr store: `$text` for free text (with a weighted text index on `title`,
`tags.name` and `notes`), equality filters for `field:value`, and organization
names resolved to ids.

**Error messages.** Routes and services choose status codes by looking for
text in the exception message:

| Text in the exception | Effect |
|---|---|
| `That name is already in use` / `That URL is already in use` | `POST /dataset` and publish retry with a timestamp suffix; `POST /kafka` and `POST /services` answer 409 |
| `not found` (any case) | 404 on show, delete and resource routes |
| `Organization not found` | 404 on `DELETE /organization/…` |
| `No scheme supplied` | 400 "Server is not configured or unreachable." |

The MongoDB backend raises CKAN's `That URL is already in use` text for a
duplicate dataset name (since 0.34.51), so duplicates behave the same on both
backends. A new backend must raise that text too.

**Organizations.** `package_create` should refuse an `owner_org` that does not
exist (CKAN does; MongoDB raises CKAN's validation-error text for it).
`DELETE /organization/…` also calls `organization_purge(id=…)` when the
repository has it and skips it otherwise.

**Creator attribution on organizations.** `GET /organization?mine=true`
reads `ndp_user_id` from each full organization, either as a top-level field
(how MongoDB stores it) or as an `extras` entry (how `CKANRepository` stores
it, after moving the keyword arguments into `extras` because CKAN rejects
unknown keys). A new backend must return it in one of those two places.

**`check_health`** is used by `/ready` (`local_catalog` check) and by
`/status/` (`backend_connected`).

---

## 4. Step by step

### 4.1 Write the repository

```python
# api/repositories/your_backend_repository.py
from typing import Any, Dict, List

from api.repositories.base_repository import DataCatalogRepository


class YourBackendRepository(DataCatalogRepository):
    """Local catalog stored in <your backend>."""

    def __init__(self, connection_string: str):
        self.client = ...  # connect; this runs on every catalog access

    # Packages
    def package_create(self, **kwargs) -> Dict[str, Any]: ...
    def package_show(self, id: str) -> Dict[str, Any]: ...
    def package_update(self, **kwargs) -> Dict[str, Any]: ...
    def package_patch(self, **kwargs) -> Dict[str, Any]: ...
    def package_delete(self, id: str) -> None: ...

    def package_search(
        self,
        q: str = "*:*",
        fq: str = "",
        rows: int = 10,
        start: int = 0,
        sort: str = "score desc, metadata_modified desc",
        **kwargs,  # fq_list arrives here
    ) -> Dict[str, Any]: ...

    # Resources
    def resource_create(self, **kwargs) -> Dict[str, Any]: ...
    def resource_show(self, id: str) -> Dict[str, Any]: ...
    def resource_delete(self, id: str) -> None: ...
    def resource_patch(self, **kwargs) -> Dict[str, Any]: ...
    # resource_search is optional; override it if the backend can do better
    # than the default scan over package_search.

    # Organizations
    def organization_create(self, **kwargs) -> Dict[str, Any]: ...
    def organization_show(self, id: str) -> Dict[str, Any]: ...
    def organization_list(
        self, all_fields: bool = False, **kwargs
    ) -> List[Dict[str, Any]]: ...
    def organization_delete(self, id: str) -> None: ...

    # Health
    def check_health(self) -> bool: ...
```

Export it from [`api/repositories/__init__.py`](../api/repositories/__init__.py)
next to `CKANRepository` and `MongoDBRepository`.

### 4.2 Register it in the factory

In [`api/config/catalog_settings.py`](../api/config/catalog_settings.py), add
its settings to `CatalogSettings` (they are read from the environment and
`.env` like the others) and a branch in `local_catalog`:

```python
class CatalogSettings(BaseSettings):
    local_catalog_backend: str = "ckan"
    mongodb_connection_string: str = "mongodb://localhost:27017"
    mongodb_database: str = "ndp_local_catalog"
    your_backend_connection_string: str = ""      # YOUR_BACKEND_CONNECTION_STRING

    @property
    def local_catalog(self) -> DataCatalogRepository:
        backend = self.local_catalog_backend.lower()

        if backend == "none":
            raise ValueError(...)                   # unchanged
        elif backend == "mongodb":
            return MongoDBRepository(...)           # unchanged
        elif backend == "ckan":
            return CKANRepository(ckan_settings.ckan)
        elif backend == "your_backend":
            return YourBackendRepository(self.your_backend_connection_string)
        else:
            raise ValueError(
                f"Unsupported catalog backend: {backend}. "
                f"Supported backends: 'ckan', 'mongodb', 'your_backend', 'none'"
            )
```

`has_local_catalog` needs no change: it is true for every value except `none`.

### 4.3 Configuration and dependencies

- Add the new variables to [`example.env`](../example.env), next to
  `LOCAL_CATALOG_BACKEND`, and to [configuration.md](configuration.md).
- Add the client library to [`requirements.txt`](../requirements.txt).
- If the backend should be offered by the installer or started by Compose,
  that is a separate change in [`install/install.sh`](../install/install.sh)
  and [`docker-compose.yml`](../docker-compose.yml).

---

## 5. Testing

### Unit tests for the repository

[`tests/repositories/`](../tests/repositories/) holds the existing backends'
tests (`test_ckan_repository.py`, `test_mongodb_repository.py`, the latter on
`mongomock`). Follow them for the new class: create, show by id and by name,
update, patch, delete, search with `q`, `fq` and `fq_list`, `rows=0`,
duplicate names, unknown organization, and `check_health` returning `False`
instead of raising.

### An integration test through the API

Routes are mounted, and settings read, when `api.main` is **imported**, so the
environment must be set before the import. This test exercises the full stack
— authentication, the write guard, the services and your repository — without
an identity provider:

```python
# tests/test_your_backend_integration.py
import os

# Before importing the app: settings and route mounting happen at import.
os.environ["LOCAL_CATALOG_BACKEND"] = "your_backend"
os.environ["YOUR_BACKEND_CONNECTION_STRING"] = "..."
os.environ["CKAN_LOCAL_ENABLED"] = "True"   # otherwise POST /dataset is not mounted
os.environ["TEST_TOKEN"] = "integration-test-token"
os.environ["ENABLE_GROUP_BASED_ACCESS"] = "False"
os.environ["AFFINITIES_ENABLED"] = "False"

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

client = TestClient(app)
AUTH = {"Authorization": "Bearer integration-test-token"}


def test_create_organization_and_dataset():
    response = client.post(
        "/organization",
        json={"name": "test-org", "title": "Test Org"},
        headers=AUTH,
    )
    assert response.status_code == 201, response.text

    response = client.post(
        "/dataset",
        json={"name": "test-dataset", "title": "Test Dataset", "owner_org": "test-org"},
        headers=AUTH,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "test-dataset"
    assert body["warning"] is None

    response = client.post(
        "/search", json={"dataset_name": "test-dataset", "server": "local"}
    )
    assert response.status_code == 200, response.text
    assert [d["id"] for d in response.json()] == [body["id"]]
```

Points that make or break it:

- **Environment before import.** If another test module in the same pytest
  session imported `api.main` first, these variables have no effect. Run the
  file on its own (`pytest tests/test_your_backend_integration.py`), or import
  the app in a subprocess the way
  [`tests/test_put_dataset_route_unique.py`](../tests/test_put_dataset_route_unique.py)
  does.
- **`TEST_TOKEN`** is accepted without calling `AUTH_API_URL` and carries
  `ndp_admin`, so it passes the writer guard.
- **`CKAN_LOCAL_ENABLED=True`** is required with any backend: without it the
  registration routes are not mounted and `POST /dataset` is 404.
- **201**, not 200, is the success status of every creation route.
- `TestClient(app)` used without `with` does not run the lifespan, so the
  metrics loop and the `services` organization bootstrap do not start.
- A `.env` in the working directory is still read for anything the test does
  not set; the environment variables above take precedence over it.

---

## 6. Code that does not go through the repository

A new backend is used by most of the API, but not all of it. As of v0.34.48
these paths reach CKAN directly, whatever `LOCAL_CATALOG_BACKEND` says:

- `api/services/organization_services/delete_organization_and_datasets.py`
  and `api/services/status_services/check_ckan_status.py` use
  `ckan_settings.ckan` directly.

Everything else — creation routes, every `PUT`/`PATCH`, services, search,
resources, deletes, publish, the metrics counts and `/ready` — goes through
`catalog_settings`.
