# Architecture overview

What an NDP Endpoint (EP) is made of and how a request moves through it, as
the code stands at **v0.34.45** (with the access-request change of 0.34.46
noted where it applies). Every statement points at the file it comes from, so
it can be checked against the code when the code moves on.

Related documents, not repeated here:

- [federation-and-metrics.md](federation-and-metrics.md) — registration with
  the NDP Federation, the configuration bootstrap and the metrics report.
- [../sequence-diagrams/](../sequence-diagrams/README.md) — step-by-step
  sequences: installing, publishing a dataset, registering and using a service.
- [../configuration.md](../configuration.md) — every environment variable.
- [../roles-and-permissions.md](../roles-and-permissions.md) — the permission model
  in detail.
- [../adding-catalog-backends.md](../adding-catalog-backends.md) — how to add
  a catalog backend.
- [../development.md](../development.md) and
  [../operations.md](../operations.md) — working on the code, and running an
  Endpoint. The index of all documents is [../README.md](../README.md).

---

## 1. The Endpoint at a glance

An Endpoint is one container that serves a React UI and a FastAPI API on the
same port. It asks the platform's AAI (`<KEYCLOAK_URL>/api`) who every
caller is, asks Keycloak what they may do, reads the global NDP catalog, and — when configured — keeps
a local catalog (CKAN or MongoDB), publishes to a staging catalog (Pre-CKAN),
manages S3 buckets, and talks to Kafka, Pelican, Affinities and the
Federation.

```mermaid
flowchart LR
    Browser["Browser / API client"]

    subgraph Container["ndp-ep-api container (port 80, published on EP_API_PORT, default 8002)"]
        Nginx["nginx :80"]
        UI["React UI (static files)<br/>/app/ui/build"]
        Uvicorn["uvicorn, 4 workers<br/>127.0.0.1:8000<br/>api.main:app"]
        Nginx -->|"ROOT_PATH/ui/"| UI
        Nginx -->|"ROOT_PATH/ and ROOT_PATH/api/"| Uvicorn
    end

    Browser --> Nginx

    Uvicorn -->|"POST token"| AAI["AAI API<br/>KEYCLOAK_URL/api"]
    Uvicorn -->|"permission decision"| Keycloak["Keycloak realm<br/>gates of OIDC_SERVICE_CLIENT_ID"]
    Uvicorn -->|read| Global["Global NDP catalog (CKAN)<br/>CKAN_GLOBAL_URL"]
    Uvicorn -->|read/write| Local["Local catalog<br/>CKAN or MongoDB"]
    Uvicorn -->|read/write| Pre["Pre-CKAN staging catalog<br/>PRE_CKAN_URL"]
    Uvicorn --> S3["S3 / MinIO<br/>S3_ENDPOINT"]
    Uvicorn --> Kafka["Kafka<br/>KAFKA_HOST:KAFKA_PORT"]
    Uvicorn --> Pelican["Pelican federations<br/>and event server"]
    Uvicorn --> Affinities["Affinities API<br/>AFFINITIES_URL"]
    Uvicorn -->|"metrics, when IS_PUBLIC"| Federation["Federation<br/>METRICS_ENDPOINT"]
    Uvicorn --> Mongo["MongoDB for access requests<br/>MONGODB_CONNECTION_STRING"]
```

Every arrow out of the container except AAI, Keycloak and the global catalog
is optional and controlled by configuration.

---

## 2. The container

Built by [`Dockerfile.allinone`](../../Dockerfile.allinone) in two stages: the
React UI is built with Node 18 (`REACT_APP_API_BASE_URL=""`, so the UI calls
the API on its own origin), then copied into a `python:3.13-slim` image with
nginx, supervisord and the Python dependencies from
[`requirements.txt`](../../requirements.txt).

### Processes

`supervisord` runs two programs (config written inline by the Dockerfile to
`/etc/supervisor/conf.d/supervisord.conf`):

| Program | Command | Logs |
|---|---|---|
| nginx | `nginx -g "daemon off;"` | `/var/log/nginx/access.log`, `/var/log/nginx/error.log` |
| uvicorn | `uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 4` | `/var/log/uvicorn.out.log`, `/var/log/uvicorn.err.log` |

uvicorn listens only on loopback; nginx on port 80 is the only way in. Each
worker also writes the application log to `logs/metrics_<start time>.log`
inside `/app` (rotating, 5 MB × 3 backups, configured at the top of
[`api/main.py`](../../api/main.py)) and to stdout.

### `entrypoint.sh`

[`entrypoint.sh`](../../entrypoint.sh) is the container's `CMD`. At every
start it:

1. Writes `/app/ui/build/config.js`, which defines `window.__EP_CONFIG__` for
   the UI from the environment: `rootPath` (`ROOT_PATH`), `affinitiesEpUuid`
   (`AFFINITIES_EP_UUID`), and the identity-provider sign-in settings
   `OIDC_ENABLED` (default `False`), `OIDC_ISSUER`, `OIDC_CLIENT_ID`,
   `OIDC_SCOPE`, `OIDC_BUTTON_LABEL`, `OIDC_HELP_TEXT`.
2. Rewrites every `"/ui/` reference in the built `index.html` to
   `"${ROOT_PATH}/ui/`.
3. Generates the nginx site `/etc/nginx/sites-available/default` from
   `ROOT_PATH` (the routing table below).
4. `exec`s supervisord.

These values are read from the process environment only; the `.env` file
reaches them because `docker-compose.yml` passes it with `env_file: .env`.

### nginx routing

| Location | Goes to | Notes |
|---|---|---|
| `${ROOT_PATH}/ui/` | static files in `/app/ui/build/` | Unknown paths fall back to `index.html` (client-side routing). |
| `= ${ROOT_PATH}/ui` | 301 to `${ROOT_PATH}/ui/` | `absolute_redirect off`, so the redirect keeps the port the client used. |
| `${ROOT_PATH}/api/` | `http://127.0.0.1:8000${ROOT_PATH}/` | Alias: `${ROOT_PATH}/api/x` reaches the API as `${ROOT_PATH}/x`. |
| `${ROOT_PATH}/` | `http://127.0.0.1:8000` | Everything else is the API; the path is passed unchanged. |

Both API locations forward `Host $http_host` (which keeps the client's port),
`X-Real-IP`, `X-Forwarded-For` and `X-Forwarded-Proto`.

**How `ROOT_PATH` is handled (since 0.34.45).** nginx passes the full path,
prefix included, and FastAPI is created with `root_path=ROOT_PATH`
([`api/main.py`](../../api/main.py),
[`api/config/swagger_settings.py`](../../api/config/swagger_settings.py)),
which removes the prefix before routing. Because FastAPI sees the prefix, the
307 redirects it issues for a missing trailing slash (`/status` →
`/status/`) keep both the prefix and the port. The OpenAPI schema lists
`ROOT_PATH` as its server URL so Swagger UI at `${ROOT_PATH}/docs` calls the
right paths. The UI itself calls the API at `${rootPath}/…` (not through the
`/api/` alias), see [`ui/src/services/api.js`](../../ui/src/services/api.js).

### Health check

Both the Dockerfile `HEALTHCHECK` and the `api` service in
[`docker-compose.yml`](../../docker-compose.yml) run
`curl -f http://localhost:8000/health` — uvicorn directly, independent of
nginx and `ROOT_PATH` — every 30 s, with a 40 s start period.

### Compose services

[`docker-compose.yml`](../../docker-compose.yml) always starts `api`
(container `ndp-ep-api`, host port `${EP_API_PORT:-8002}` → 80). Everything
else is behind a profile, and `full` starts all of them:

| Profile | Service (container) | Host ports → container | Notes |
|---|---|---|---|
| `mongodb` | `mongodb` (`ndp-mongodb`), `mongo:7` | 27018 → 27017 | Root user `admin` / `admin123`; the Endpoint reaches it as `mongodb://admin:admin123@mongodb:27017`. |
| `mongo-express` | `mongo-express` (`ndp-mongo-express`) | 8082 → 8081 | Web UI for the bundled MongoDB; never started by the installer. |
| `s3` | `minio` (`ndp-minio`), `pgsty/silo:RELEASE.2026-09-16T00-00-00Z` | 9002 → 9000 (API), 9003 → 9001 (console) | Community fork of MinIO, same API and `MINIO_*` variables; `minioadmin` / `minioadmin123`. |
| `kafka` | `zookeeper`, `kafka` (`ndp-kafka`), `confluentinc/cp-kafka:7.6.0` | 9094 → 9092, 9095 → 9093 | Inside the network the Endpoint uses `kafka:9093`. |
| `kafka` | `kafka-ui` | 8081 → 8080 | Web UI for the bundled Kafka. |
| `jupyter` | `jupyterlab` | 8888 → 8888 | `jupyter/scipy-notebook`. |
| `pelican` | `pelican-registry`, `pelican-director`, `pelican-origin`, `pelican-cache` | 8444–8449 | A local Pelican federation; the origin mounts the MinIO volume read-only. |

All services share the `ndp-network` bridge network.

---

## 3. Code layout

```
api/
├── main.py            App creation, middleware, router mounting, lifespan, MCP
├── config/            Settings classes (pydantic-settings) and the catalog factory
├── middleware/        CorrelationIdMiddleware
├── exceptions/        Global exception handlers (error envelope)
├── models/            Pydantic request/response models
├── routes/            HTTP routes, one package per group
├── services/          Business logic, one package per domain
├── repositories/      Catalog backends (CKAN, MongoDB), Pelican, access requests
├── tasks/             Background work: leader election, metrics loop
└── telemetry/         Optional OpenTelemetry setup
ui/                    React UI (built into the image)
install/               Installer (install.sh) and its helpers
tests/                 pytest suite
```

---

## 4. How a request flows

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant N as nginx :80
    participant M as Middleware<br/>(OTel*, correlation id, CORS)
    participant R as Route
    participant D as Auth dependency
    participant A as AAI API (KEYCLOAK_URL/api)
    participant K as Keycloak realm
    participant S as Service
    participant P as Repository / external system

    C->>N: request to ROOT_PATH/… with Authorization: Bearer token
    N->>M: proxy to 127.0.0.1:8000 (full path)
    M->>M: root_path strips ROOT_PATH, X-Correlation-ID read or generated
    M->>R: routed request
    R->>D: Depends(get_current_user / ep_*_gate)
    alt token == TEST_TOKEN
        D-->>D: fixed admin user (no AAI call)
    else
        D->>A: POST /information with the token
        A-->>D: user info (sub, username, …)
        D->>K: UMA decision for the route's gate on OIDC_SERVICE_CLIENT_ID
        K-->>D: {"result": true}, 403, or 401
    end
    D-->>R: user_info, or 401/403/502
    R->>S: call service
    S->>P: catalog / S3 / Kafka / Affinities …
    P-->>S: result or exception
    S-->>R: result
    R-->>M: JSON (or HTTPException → error envelope)
    M-->>C: response + X-Correlation-ID header
```

\* OpenTelemetry only when `OTEL_ENABLED=true`.

### Middleware and error handling

Registered in [`api/main.py`](../../api/main.py), in this order:

1. `setup_telemetry(app)` ([`api/telemetry/setup.py`](../../api/telemetry/setup.py))
   — instruments FastAPI, `httpx` and `requests` when `OTEL_ENABLED` is true;
   exporter `console`, `otlp` or `none`.
2. `CorrelationIdMiddleware` ([`api/middleware/correlation_id.py`](../../api/middleware/correlation_id.py))
   — takes `X-Correlation-ID` from the request or generates a UUID4, keeps it
   in a context variable for the request, and returns it in the
   `X-Correlation-ID` response header.
3. `CORSMiddleware` — all origins, methods and headers, credentials allowed.

[`api/exceptions/handlers.py`](../../api/exceptions/handlers.py) registers
handlers for `HTTPException`, `RequestValidationError`/`ValidationError` (422)
and any other `Exception` (500). All of them answer with the same envelope:

```json
{
  "error": "NotFound",
  "detail": "Resource not found",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-10-08T12:00:00.000000+00:00",
  "path": "/resource/abc"
}
```

`error` is derived from the status code (`BadRequest`, `Unauthorized`,
`Forbidden`, `NotFound`, `MethodNotAllowed`, `Conflict`, `ValidationError`,
`InternalServerError`, `BadGateway`, `ServiceUnavailable`, `GatewayTimeout`,
otherwise `HTTPError`). Validation errors carry a list of
`{loc, msg, type}` in `detail`. Unhandled exceptions are logged with their
traceback and answered with a generic message.

### Authentication

[`get_current_user`](../../api/services/auth_services/get_current_user.py) is
the single source of identity. It uses FastAPI's `HTTPBearer`, so a request
without an `Authorization: Bearer …` header is rejected before it runs.

- If `TEST_TOKEN` is set (it is empty, so off, by default) and the token
  equals it, it returns a
  fixed user — `sub: test_user`, `username: Test User`,
  `roles: ["ndp_admin"]`, `groups: []` — without contacting the AAI. That
  token passes every permission gate without asking Keycloak, so the user is
  a full administrator.
- Otherwise it sends `POST <KEYCLOAK_URL>/api/information` with
  `{"token": "<token>"}` (10 s timeout). AAI 400/401/403 and a body
  containing `error` become **401**; AAI 500,
  any other non-200, an unreachable AAI, or an unexpected failure become
  **502**. A response without `sub` gets `sub: "unknown"`.

The user payload is passed through as returned by the AAI (`roles`, `groups`,
`sub`, `username`, …); its `roles` and `groups` are not used for
authorization. The Endpoint keeps no session; every authenticated request
calls the AAI again.

Username/password sign-in (`POST /user/login`, and the form-encoded
`POST /token` alias) is proxied to `<KEYCLOAK_URL>/api/user/login`
by [`user_login.py`](../../api/services/auth_services/user_login.py).

### Authorization

Keycloak decides. `ep_access_gate` in
[`ep_access_gate.py`](../../api/services/auth_services/ep_access_gate.py),
named after the Federation's function and raising like it, asks the realm,
with the caller's own token, whether they pass one of the
three gates of the Endpoint's client `OIDC_SERVICE_CLIENT_ID` (`ep-<config-id>`):
`POST <realm>/protocol/openid-connect/token` with the UMA grant,
`audience=<OIDC_SERVICE_CLIENT_ID>`, `permission=<gate>` and
`response_mode=decision`, as the Federation does. `<realm>` is
`<KEYCLOAK_URL>/realms/<AUTHZ_REALM>`. Only `{"result": true}`
grants; Keycloak refusing, or no `OIDC_SERVICE_CLIENT_ID`, is **403**, rejecting the
token **401**, failing or unreachable **502**. No client secret is involved.

| Tier | Gate | Passed by the Endpoint group's |
|---|---|---|
| admin | `admin-area` | admins |
| writer | `editor-area` | admins, editors |
| viewer | `viewer-area` | admins, editors, viewers |

Keycloak evaluates live group membership; levels on parent groups count
(those whose subgroup existed when the gates were set up) and `ndp_admin`
passes every gate of a client the AAI created (a client linked later with
`tools/adopt_client.py` has no `ndp_admin` policy). With `OIDC_SERVICE_CLIENT_ID` set, `/user/info`
additionally requires a tier.

The FastAPI dependencies, in
[`ep_access_gate.py`](../../api/services/auth_services/ep_access_gate.py)
and [`get_current_user.py`](../../api/services/auth_services/get_current_user.py):

| Dependency | Gate | Used by |
|---|---|---|
| `get_current_user` | none (authenticated only) | `/status/*` (except `/status/rexec`), `/user/access-requests` (create), `/organization?mine=true` (optional token) |
| `ep_viewer_gate` | `viewer-area` | every `/pelican/*` route (router-level dependency) |
| `ep_editor_gate` | `editor-area` | every POST/PUT/PATCH/DELETE on the catalog, `/dataset/{id}/publish`, all `/s3/*` routes (reads included), `/status/rexec`, `/pelican/import-metadata` |
| `ep_admin_gate` | `admin-area` | listing, approving and rejecting access requests |

Catalog reads — `GET /search`, `POST /search`, `GET /organization`,
`GET /resource/{id}`, `GET /resources/search` — take no token.
`/user/info` (authenticated only; with `OIDC_SERVICE_CLIENT_ID` set it also
requires a tier) adds `effective_role` (`admin`/`writer`/`viewer`/`none`,
the highest gate passed) and
`ndp_user_id` (first 16 hex characters of SHA-256 of `sub`) to the AAI
payload. See [../roles-and-permissions.md](../roles-and-permissions.md).

---

## 5. Route groups and when they are mounted

Mounted in [`api/main.py`](../../api/main.py) at import time, from settings
read at import time. Changing a switch needs a restart.

`local_catalog_enabled = CKAN_LOCAL_ENABLED and LOCAL_CATALOG_BACKEND != "none"`

| Router (`api/routes/…`) | Mounted when | Paths |
|---|---|---|
| `default_routes` | always (hidden from the schema) | `GET /` |
| `health_routes` | always | `GET /health`, `GET /ready` |
| `register_routes` | `local_catalog_enabled` | `POST /organization`, `/dataset`, `/url`, `/s3`, `/kafka`, `/services`, `/dataset/{id}/publish` |
| `search_routes` | always | `GET /search`, `POST /search`, `GET /organization` |
| `update_routes` | `local_catalog_enabled` | `PUT`/`PATCH` `/dataset/{id}`, `/url/{id}`, `/s3/{id}`, `/kafka/{id}`, `/services/{id}`; `PATCH /dataset/{id}/resource/{rid}` |
| `delete_routes` | `local_catalog_enabled` | `DELETE /resource?resource_id=`, `/resource/{name}`, `/organization/{name}`, `/dataset/{id}/resource/{rid}` |
| `resource_routes` | `local_catalog_enabled` | `GET`/`PATCH /resource/{id}`, `GET /resources/search` |
| `redirect_routes` | always | `/services/redirect/{name}[/{path}]` — reverse proxy to a registered service; methods GET/POST/PUT/PATCH/DELETE |
| `status_routes` (prefix `/status`) | always | `GET /status/`, `/status/metrics`, `/status/version`, `/status/kafka-details`; plus `/status/jupyter` if `USE_JUPYTERLAB`, `/status/rexec` if `REXEC_CONNECTION` |
| `user_routes` | always | `GET /user/info`, `POST /user/login`, `POST /token`, `/user/access-requests[...]` |
| `minio_routes` | `S3_ENABLED` | `/s3/buckets/…`, `/s3/objects/…` |
| `pelican_routes` (prefix `/pelican`) | `PELICAN_ENABLED` (read with `os.getenv`) | `federations`, `browse`, `info`, `download`, `read`, `subscribe`, `subscriptions`, `import-metadata` |

The access-request routes are always mounted and answer 503 while
`ENABLE_ACCESS_REQUESTS` is false. `GET /search?server=local` answers 400 when
`CKAN_LOCAL_ENABLED` is false. The service proxy authenticates the caller only
when the target service's `requires_auth` extra is truthy
([`redirect_service.py`](../../api/services/service_services/redirect_service.py)).

### MCP

`FastApiMCP(app).mount_http()` (package `fastapi-mcp`) mounts a Model Context
Protocol server on the same app at `/mcp`. It exposes the operations in the
app's OpenAPI schema as MCP tools, so it follows whatever routes are mounted;
the routes hidden from the schema (`GET /` and the functional service-proxy
routes) are not part of it. `mcp<2.0.0` is pinned in `requirements.txt`
because `fastapi-mcp` 0.4.0 fails at import with mcp 2.

---

## 6. The three catalogs

| Catalog | Backend | Configured by | Used for |
|---|---|---|---|
| **Global** | Always CKAN, no API key | `CKAN_GLOBAL_URL` (default `https://nationaldataplatform.org/catalog`) | Searching the platform catalog (`server=global`, the default of `GET /search`, `POST /search` and `GET /organization`). No route writes to it. |
| **Local** | CKAN, MongoDB or none | `LOCAL_CATALOG_BACKEND`, `CKAN_URL`/`CKAN_API_KEY` or `MONGODB_*`; writes switched on by `CKAN_LOCAL_ENABLED` | Everything this Endpoint publishes (`server=local`, the default of every write route). |
| **Pre-CKAN** (staging) | Always CKAN | `PRE_CKAN_ENABLED`, `PRE_CKAN_URL`, `PRE_CKAN_API_KEY`, `PRE_CKAN_ORGANIZATION` | Datasets promoted for review: `POST /dataset/{id}/publish` copies a local dataset there, and write routes accept `server=pre_ckan`. |

With `LOCAL_CATALOG_BACKEND=none` there is no local catalog: the catalog
write routes are not mounted, `/ready` reports the local catalog `disabled`,
the metrics report counts 0 datasets and services, and the startup creation of
the `services` organization is skipped.

The flow of a dataset through the three is drawn in
[../sequence-diagrams/publishing-a-dataset.md](../sequence-diagrams/publishing-a-dataset.md).

---

## 7. The repository pattern

Catalog access goes through one interface so that the services do not depend
on the backend.

```mermaid
classDiagram
    class DataCatalogRepository {
        <<abstract>>
        package_create(kwargs)
        package_show(id)
        package_update(kwargs)
        package_patch(kwargs)
        package_delete(id)
        package_search(q, fq, rows, start, sort, kwargs)
        resource_create(kwargs)
        resource_show(id)
        resource_delete(id)
        resource_patch(kwargs)
        resource_search(...)  default implementation
        organization_create(kwargs)
        organization_show(id)
        organization_list(all_fields, kwargs)
        organization_delete(id)
        check_health()
    }
    DataCatalogRepository <|-- CKANRepository
    DataCatalogRepository <|-- MongoDBRepository
    class CatalogSettings {
        local_catalog_backend
        has_local_catalog
        local_catalog
        global_catalog
        pre_catalog
        get_repository_by_name(name)
    }
    CatalogSettings ..> CKANRepository : creates
    CatalogSettings ..> MongoDBRepository : creates
```

- **Interface** — [`api/repositories/base_repository.py`](../../api/repositories/base_repository.py),
  `DataCatalogRepository`. Abstract methods: `package_create`, `package_show`,
  `package_update`, `package_patch`, `package_delete`, `package_search`,
  `resource_create`, `resource_show`, `resource_delete`, `resource_patch`,
  `organization_create`, `organization_show`, `organization_list`,
  `organization_delete`, `check_health`. `resource_search` is concrete: its
  default walks `package_search(q="*:*", rows=1000)` and filters resources in
  Python; a backend may override it. The data shapes follow CKAN's action API
  (`extras` as `[{"key", "value"}]`, `tags` as `[{"name"}]`,
  `package_search` returning `{"count", "results"}`).
- **CKAN** — [`api/repositories/ckan_repository.py`](../../api/repositories/ckan_repository.py),
  `CKANRepository(ckan_instance)`, a thin delegation to a `ckanapi.RemoteCKAN`
  (`ckan.action.<name>`). `check_health` calls `status_show`.
  `organization_delete` purges the organization.
- **MongoDB** — [`api/repositories/mongodb_repository.py`](../../api/repositories/mongodb_repository.py),
  `MongoDBRepository(connection_string, database_name)`. Collections
  `packages`, `resources` and `organizations`; resources are stored in their
  own collection and also embedded in the package's `resources` array.
  Indexes, created on every construction: unique `packages.name`,
  `packages.owner_org`, unique `organizations.name`, `resources.package_id`,
  and a weighted text index `fulltext_search_index` on `title` (10),
  `tags.name` (5) and `notes` (1). Since 0.34.39 the text index uses
  `tags.name` and an existing index with different fields is dropped and
  rebuilt at start. `package_search` turns a free-text `q` into a `$text`
  query sorted by `textScore`; a `q` made only of `field:value` parts joined
  by ` AND ` (and every `fq`/`fq_list` entry) becomes equality filters, with
  `organization` mapped to `owner_org` and organization names resolved to
  ids. It overrides `resource_search` with its own query.
  `package_create` rejects an `owner_org` that does not exist with CKAN's
  validation-error text, and a duplicate name with
  `Package with name '<name>' already exists`. `check_health` pings the
  server.
- **Factory** — [`api/config/catalog_settings.py`](../../api/config/catalog_settings.py),
  `catalog_settings` (`CatalogSettings`). `local_catalog` returns
  `MongoDBRepository` for `mongodb`, `CKANRepository(ckan_settings.ckan)` for
  `ckan`, and raises `ValueError` for `none` or an unknown value;
  `has_local_catalog` is false only for `none`. `global_catalog` and
  `pre_catalog` always return a `CKANRepository`. The properties build a new
  repository object on each access (for MongoDB, a new `MongoClient` and the
  index checks).

`api/repositories/` also holds two classes that are not catalog backends:
`PelicanRepository` (wraps `pelicanfs`) and `AccessRequestRepository` (the
MongoDB collection behind access requests).

---

## 8. Services

Routes are thin; the logic is in [`api/services/`](../../api/services/):

| Package | Responsibility |
|---|---|
| `auth_services` | `get_current_user`, the authorization dependencies, username/password login, and `aai_client` (the AAI calls used to grant access requests) |
| `access_request_services` | The access-request workflow (create, list, approve via the AAI, reject) |
| `dataset_services` | General datasets (create/update/patch, reserved extras, auto-rename on duplicate names), resource get/patch/delete/search, dataset delete, publish to Pre-CKAN |
| `datasource_services` | Search: `search_datasets_by_terms` (`GET /search`) and `search_datasource` (`POST /search`), plus the generic `add_datasource` |
| `url_services`, `s3_services`, `kafka_services`, `service_services` | Register and update datasets that describe a URL, an S3 object, a Kafka topic or a service; `redirect_service` resolves a service for the proxy |
| `organization_services` | Create, list (optionally by creator hash), delete (with or without cascade) |
| `metadata_services` | Injects `ndp_group_id`, `ndp_user_id` and `ndp_creator_md5` into new datasets' extras and keeps them unchanged on updates |
| `minio_services` | MinIO client (`minio` package), bucket and object operations |
| `pelican_services` | Browse, read, download, import metadata, and STOMP-over-WebSocket file-event subscriptions |
| `affinities_services` | `AffinitiesClient` |
| `status_services` | `/status/` contents, system metrics, catalog counts for the metrics report |

---

## 9. Background work

The FastAPI lifespan in [`api/main.py`](../../api/main.py) runs once per
uvicorn worker, and there are four. Work that must happen once per Endpoint is
done by a single **leader** worker
([`api/tasks/leader.py`](../../api/tasks/leader.py), since 0.34.38):

- At startup each worker tries a non-blocking exclusive `flock` on
  `<tmpdir>/ndp-ep-leader.lock`. The one that gets it is the leader; the
  others poll every 30 s and take over when the lock is released (the lock
  belongs to the process, so it is released however the leader stops).
- The leader creates the local catalog's `services` organization if it is
  missing (only when `local_catalog_enabled`), then runs
  `record_system_metrics()` ([`api/tasks/metrics_task.py`](../../api/tasks/metrics_task.py)):
  every `METRICS_INTERVAL_SECONDS` (default 3300) it collects public IP, CPU,
  memory, disk, version, organization, Endpoint name, dataset and service
  counts, enabled features and NetBird/CKAN deployment details, logs them,
  and — only when `IS_PUBLIC` is true — POSTs them to `METRICS_ENDPOINT`.
  The report and the Federation side are described in
  [federation-and-metrics.md](federation-and-metrics.md).

Every worker, leader or not, also tests the S3 connection at startup when
`S3_ENABLED` is true and logs the result.

---

## 10. Integrations

| Integration | Switch | Code | What the Endpoint does |
|---|---|---|---|
| AAI | always | `auth_services/get_current_user.py`, `user_login.py`, `aai_client.py` | Says who every token belongs to; proxies username/password login; on access-request approval calls `POST /group/add-user` with the approving admin's token, on the Endpoint's group `ndp_ep/<OIDC_SERVICE_CLIENT_ID>`. All under `<KEYCLOAK_URL>/api`. |
| Federation | `IS_PUBLIC` | `tasks/metrics_task.py` | Posts the periodic metrics report. Registration happens in the installer, not in the API. |
| Affinities | `AFFINITIES_ENABLED` + `AFFINITIES_URL` + `AFFINITIES_EP_UUID` | `affinities_services/affinities_client.py` | After `POST /dataset` and `POST /services` (for `server=local` and `server=pre_ckan`), registers the record, links it to this Endpoint, creates an affinity triple, and stores the returned UUID as the `ndp_affinity_uuid` extra. Failures are logged and never fail the request. `/ready` reports whether Affinities knows `AFFINITIES_EP_UUID`. See [../affinities-integration.md](../affinities-integration.md). |
| Pelican | `PELICAN_ENABLED` | `routes/pelican_routes.py`, `repositories/pelican_repository.py`, `pelican_services/` | Browses and reads federations (OSDF by default, or `PELICAN_FEDERATION_URL`), streams downloads, imports a Pelican object as a resource of a local dataset, and relays file events from the event server. |
| Kafka | `KAFKA_CONNECTION` | `kafka_services/`, `routes/status_routes/kafka_details.py`, `routes/health_routes/ready.py` | Stores datasets that describe a topic (`POST /kafka`, metadata only — the API does not create topics or consume messages); advertises host, port, `KAFKA_PREFIX` and `MAX_STREAMS` at `/status/kafka-details`; `/ready` opens a `kafka-python` producer to check the broker. |
| S3 / MinIO | `S3_ENABLED` | `minio_services/`, `routes/minio_routes/` | Bucket and object management through the `minio` client; `POST /s3` separately registers a catalog dataset that points at an S3 URL. See [../minio-setup.md](../minio-setup.md). |
| Remote execution | `REXEC_CONNECTION` | `routes/status_routes/get_rexec_api.py` | Exposes `REXEC_DEPLOYMENT_API_URL` to writers; the API does not call it. |
| JupyterLab | `USE_JUPYTERLAB` | `routes/status_routes/get_jupyter.py` | Exposes `JUPYTER_URL`; the API does not call it. |
| OpenTelemetry | `OTEL_ENABLED` | `telemetry/setup.py` | Traces requests and outgoing `httpx`/`requests` calls. |
| MCP | always | `api/main.py` | See §5. |

---

## 11. Health

- `GET /health` — liveness. Always 200 with `{"status": "healthy", "timestamp"}`;
  checks nothing.
- `GET /ready` — readiness ([`ready.py`](../../api/routes/health_routes/ready.py)).
  Checks `local_catalog` (`disabled` without a local catalog or with
  `CKAN_LOCAL_ENABLED` false), `pre_ckan`, `minio`, `kafka` and
  `affinities`, each `up`/`down`/`disabled` with latency. Answers **503** when
  any enabled check other than Affinities is down. Affinities is reported
  (including `endpoint_registered`) but never changes the verdict; its probe
  is cached for 30 s and limited to 5 s.
- `GET /status/` and `GET /status/metrics` (authenticated) — configuration
  summary and system metrics for the UI.

---

## 12. Configuration

Settings are `pydantic-settings` classes in [`api/config/`](../../api/config/),
each instantiated once at import as a module-level singleton:

| Module | Object | Variables |
|---|---|---|
| `swagger_settings.py` | `swagger_settings` | `ROOT_PATH`, `ORGANIZATION`, `EP_NAME`, `IS_PUBLIC`, `METRICS_*`, `USE_JUPYTERLAB`, `JUPYTER_URL`, `TEST_TOKEN`, `KEYCLOAK_URL` (`AUTH_API_URL` still read), `OIDC_SERVICE_CLIENT_ID`, `OIDC_SERVICE_CLIENT_SECRET`, `AUTHZ_REALM`, `ENABLE_ACCESS_REQUESTS`, `ACCESS_REQUESTS_COLLECTION`, `SWAGGER_*` (the version is the default of `swagger_version`) |
| `catalog_settings.py` | `catalog_settings` | `LOCAL_CATALOG_BACKEND`, `MONGODB_CONNECTION_STRING`, `MONGODB_DATABASE` |
| `ckan_settings.py` | `ckan_settings` | `CKAN_LOCAL_ENABLED`, `CKAN_URL`, `CKAN_API_KEY`, `CKAN_VERIFY_SSL`, `CKAN_GLOBAL_URL`, `PRE_CKAN_*` |
| `minio_settings.py` | `s3_settings` | `S3_*` |
| `kafka_settings.py` | `kafka_settings` | `KAFKA_CONNECTION`, `KAFKA_HOST`, `KAFKA_PORT`, `KAFKA_PREFIX`, `MAX_STREAMS` |
| `affinities_settings.py` | `affinities_settings` | `AFFINITIES_*` |
| `rexec_settings.py` | `rexec_settings` | `REXEC_*` |
| `otel_settings.py` | `otel_settings` | `OTEL_*` |

All of these except `OTelSettings` also read a `.env` file in the working
directory; environment variables take precedence. Unknown variables are
ignored. Some values are read directly with `os.getenv` and therefore only
from the **process environment**: `PELICAN_*` (including `PELICAN_ENABLED`),
`NETBIRD_*`, and `AFFINITIES_EP_UUID` where it is the fallback event-client
id. `OTEL_*` and everything `entrypoint.sh` reads (`ROOT_PATH`, `OIDC_*`,
`AFFINITIES_EP_UUID` for the UI) are also process-environment only. In the
container this makes no difference, since Compose loads `.env` into the
environment; it matters when uvicorn is run directly from a checkout.

Each variable is described in [../configuration.md](../configuration.md).
