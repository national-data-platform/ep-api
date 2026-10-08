# Connector nodes — inventory of the Endpoint's building blocks

Input for the connector-node design (Jira PASS-84). It lists what an NDP
Endpoint (EP) is made of, how tightly each piece is tied to the rest, and
whether it could be reused in a **connector node**.

> **"Connector node" is not defined yet** (open decision Q5). For this
> document it is taken to mean *a minimal node that exposes local data or
> services to the NDP without running a full Endpoint*. Every reuse verdict
> below depends on that assumption and should be revisited once Q5 is
> decided.

**Summary**

- 19 building blocks, most of which can already be switched off by
  configuration; the main exceptions are the core API, global search, the
  service proxy, the MCP server and the UI.
- The pieces closest to what an external node would need are the
  config-id installer bootstrap, the metrics loop (as a future heartbeat),
  authentication, and the ways of exposing data: catalog, S3, Pelican and the
  service proxy.
- What a connector node is has not been decided (Q5); the verdicts below are
  provisional and the open questions at the end are what that decision has to
  answer.

Read from ep-api **v0.34.46**. Each row separates **Facts** (read from the
code, with a reference) from **Assessment** (judgement about reuse, which is
an opinion, not a fact). The Federation's own building blocks are inventoried
in `sci-ndp/ndp-federation` (`docs/CONNECTOR_NODES.md`); how an Endpoint talks
to the Federation is in [federation-and-metrics.md](federation-and-metrics.md).

Reuse verdicts:

- **as-is** — usable in a connector node without code changes, by
  configuration alone;
- **adapt** — the logic is reusable but needs extracting, a smaller
  dependency set, or a change of contract;
- **not applicable** — belongs to the full Endpoint experience, not to a
  minimal node.

## Summary

| # | Component | Can be switched off today? | Verdict |
|---|---|---|---|
| 1 | Core API process (FastAPI, middleware, errors) | no | adapt |
| 2 | Authentication and roles (AAI) | group gate only; auth itself no | as-is |
| 3 | Identity-provider sign-in (OIDC, UI) | yes, `OIDC_ENABLED` | not applicable |
| 4 | Local catalog (repository pattern: CKAN / MongoDB / none) | yes, `LOCAL_CATALOG_BACKEND=none` | adapt |
| 5 | Global catalog search | no | not applicable |
| 6 | Publishing to the staging catalog (pre-CKAN) | yes, `PRE_CKAN_ENABLED` | adapt |
| 7 | Object storage (S3 / MinIO) | yes, `S3_ENABLED` | as-is |
| 8 | Kafka | yes, `KAFKA_CONNECTION` | adapt |
| 9 | Pelican / OSDF | yes, `PELICAN_ENABLED` | as-is |
| 10 | Remote execution (rexec) | yes, `REXEC_CONNECTION` | not applicable |
| 11 | JupyterLab link | yes, `USE_JUPYTERLAB` | not applicable |
| 12 | Service registry and proxy | no | adapt |
| 13 | MCP server (`/mcp`) | no | adapt |
| 14 | Metrics / heartbeat | posting yes (`IS_PUBLIC`), collection no | adapt |
| 15 | Affinities client | yes, `AFFINITIES_ENABLED` | as-is |
| 16 | Access requests | yes, `ENABLE_ACCESS_REQUESTS` | not applicable |
| 17 | Web UI | no | not applicable |
| 18 | Installer and Federation bootstrap | — | adapt |
| 19 | Packaging (image and compose profiles) | profiles yes | adapt |

## Components

### 1. Core API process

**Facts**
- One FastAPI app (`api/main.py:137-143`) with CORS, a correlation-id
  middleware and global exception handlers (`145-160`); OpenTelemetry is
  optional (`OTEL_ENABLED`, `api/config/otel_settings.py:7-17`).
- Routers are mounted conditionally at import time: the registration, update,
  delete and resource routes only when `CKAN_LOCAL_ENABLED` and a local
  backend exist (`api/main.py:58-60`, `164-172`), S3 with `S3_ENABLED`
  (`176-178`), Pelican with `PELICAN_ENABLED` (`180-185`). `/`, `/health`,
  `/ready`, search, status, user and service-redirect routes are always
  mounted (`162-175`); within status, `/status/jupyter` and `/status/rexec`
  follow `USE_JUPYTERLAB` and `REXEC_CONNECTION`
  (`api/routes/status_routes/__init__.py`).
- Runs as four uvicorn workers behind nginx in one container
  (`Dockerfile.allinone:53-73`); the nginx site is generated from `ROOT_PATH`
  by `entrypoint.sh` at every start. Since 0.34.38 the once-per-Endpoint
  startup work — creating the `services` organization and the metrics loop —
  runs only in the worker that holds a file lock (`api/tasks/leader.py`,
  `api/main.py:92-134`); other per-process state (the Affinities
  registration cache, the Pelican event client) still exists once per
  worker.

**Assessment** — *adapt*. The conditional mounting already gives a "profile"
mechanism; a connector node would want it explicit (a named profile). The
leader lock is the existing way to keep a background loop to one worker.

### 2. Authentication and roles (AAI)

**Facts**
- Every protected route validates the bearer token by `POST AUTH_API_URL
  {"token": …}` (`api/services/auth_services/get_current_user.py:60-61`); no
  local JWT validation.
- Tiers viewer / writer / admin, from `ndp_*` roles or
  `group:<GROUP_NAMES entry | AFFINITIES_EP_UUID>:<tier>`; the identity
  provider's `editor` tier counts as writer
  (`api/services/auth_services/authorization_service.py`).
- `ENABLE_GROUP_BASED_ACCESS` + `GROUP_NAMES` add a membership gate; the
  installer sets them from the registration's group
  (`install/install.sh:1095-1098`). The gate decides who may enter the
  Endpoint (`GET /user/info`, which the UI calls at sign-in) and applies to
  every write; writes also need the writer tier.
- `TEST_TOKEN` bypasses the AAI and grants `ndp_admin`
  (`get_current_user.py:44-56`).

**Assessment** — *as-is*. Self-contained, configured by environment only, and
the same trust model a connector node would need. The `TEST_TOKEN` default
should not travel to a minimal node.

### 3. Identity-provider sign-in (OIDC, UI)

**Facts** — A PKCE login button in the UI, configured through `OIDC_*`
variables injected by `entrypoint.sh` (`ui/src/services/oidc.js:49-70`); the
token is still validated through `AUTH_API_URL`. The installer forces it off
because the client a registration creates cannot be used for it
(`install/install.sh:1042`, `1138-1144`).

**Assessment** — *not applicable*: a UI feature.

### 4. Local catalog (repository pattern)

**Facts**
- Abstract `DataCatalogRepository` (`api/repositories/base_repository.py`)
  with CKAN and MongoDB implementations; `LOCAL_CATALOG_BACKEND=ckan|mongodb|none`
  selects one (`api/config/catalog_settings.py:18-102`).
- `none` unmounts every write route and is the installer's default.
- Datasets, URL/S3/Kafka resources and services are all stored through this
  interface.

**Assessment** — *adapt*. The interface is the natural way for a connector
node to describe what it exposes, and MongoDB is the lighter backend. Whether
a connector node keeps a catalog at all, or only pushes descriptions to a
central one, is part of Q5.

### 5. Global catalog search

**Facts** — `GET /search` reads the NDP global CKAN through
`CKAN_GLOBAL_URL` (`api/config/ckan_settings.py:13`, `37-38`) by default, and
the local catalog with `server=local` (400 when `CKAN_LOCAL_ENABLED` is off);
`POST /search` also accepts `server=pre_ckan` when `PRE_CKAN_ENABLED` is on
(`api/routes/search_routes/search_datasource_route.py:83-141`,
`post_search_datasource_route.py:58-62`). Always mounted (`api/main.py:166`).

**Assessment** — *not applicable* for the global part: it is a consumer
feature; a connector node exposes data rather than browsing the platform.

### 6. Publishing to the staging catalog (pre-CKAN)

**Facts** — `POST /dataset/{id}/publish` copies a local dataset to the
staging catalog using credentials from the Federation registration
(`PRE_CKAN_*`, `install/install.sh:1121-1134`). The registration, update and
delete routes also accept `?server=pre_ckan`, which writes straight to the
staging catalog without a local copy (for example
`api/routes/register_routes/post_general_dataset.py:196-202`). All of them
live under routers that are mounted only with a local catalog.

**Assessment** — *adapt*. Publishing is close to what a connector node must
do, but today it depends on a local catalog and on a per-Endpoint CKAN key
handed out by the Federation. Jira PASS-93/PASS-95 (publish as the Endpoint,
through the `/ndp` endpoints rather than a CKAN key) would change this
contract.

### 7. Object storage (S3 / MinIO)

**Facts** — Bucket and object CRUD and presigned URLs over the `minio` SDK
(`api/services/minio_services/`), all writer-only
(`api/routes/minio_routes/bucket_routes.py:16-96`); switched by
`S3_ENABLED`; the bundled server is the `s3` compose profile
(`pgsty/silo`, a MinIO fork).

**Assessment** — *as-is*. Independent of the rest and a plausible way for a
node to expose files.

### 8. Kafka

**Facts**
- A Kafka topic is registered as catalog metadata (host, port, topic as
  extras); there is **no Kafka client** in the request path.
- The only client use is the readiness check
  (`api/routes/health_routes/ready.py:138-159`), a `KafkaProducer` from
  `kafka-python` (`requirements.txt:39`, `kafka-python>=3.0`); since 0.34.42
  the check runs.
- `KAFKA_CONNECTION` gates the readiness check and the metrics fields.
  `GET /status/kafka-details` is always mounted
  (`api/routes/status_routes/__init__.py`); only `POST /kafka` and its
  `PUT`/`PATCH /kafka/{dataset_id}` follow the local-catalog switch, because
  they live in the registration and update routers.

**Assessment** — *adapt*: today it is metadata only. Exposing streams from a
connector node would need an actual client or a bridge.

### 9. Pelican / OSDF

**Facts** — `/pelican/*` routes to browse, read, download and import metadata
from Pelican federations, plus event subscriptions over a STOMP websocket
(`api/routes/pelican_routes.py`, `api/services/pelican_services/`); viewer
auth on the router (`pelican_routes.py:52-56`); switched by
`PELICAN_ENABLED`. A separate `pelican` compose profile runs a
registry/director/origin/cache stack.

**Assessment** — *as-is* for the read side. Pelican is already a federation of
data origins, so an origin serving local data could itself be the "exposure"
half of a connector node; the event client keys itself on
`PELICAN_EVENT_CLIENT_ID` and falls back to `AFFINITIES_EP_UUID`
(`api/services/pelican_services/event_subscription.py:128-132`), which
installs leave empty.

### 10. Remote execution (rexec)

**Facts** — `GET /status/rexec` returns the configured
`REXEC_DEPLOYMENT_API_URL` (`api/config/rexec_settings.py`), mounted only with
`REXEC_CONNECTION`; no client calls. The Federation stores the flag but not
the URL.

**Assessment** — *not applicable* as code (it is a link). The concept —
the node advertises a compute capability — may matter for Q5.

### 11. JupyterLab link

**Facts** — `/status/jupyter` (mounted only with `USE_JUPYTERLAB`) and a UI
card pointing at `JUPYTER_URL`; `jupyter` compose profile.

**Assessment** — *not applicable*.

### 12. Service registry and proxy

**Facts** — Services are registered in the local catalog; `GET
/services/redirect/{id}[/{path}]` proxies to them with httpx
(`api/routes/redirect_routes/service_redirect.py`), applying auth only when
the service's `requires_auth` asks for it; 30-second timeout (504), 502 when
the service cannot be reached. Always mounted (`api/main.py:173`).

**Assessment** — *adapt*. A proxy in front of local services is close to
the "exposes services" half of a connector node, but the registry depends on
the local catalog and the proxy forwards request headers unchanged.

### 13. MCP server

**Facts** — `FastApiMCP(app).mount_http()` exposes every API route as an MCP
tool at `/mcp` (`api/main.py:188-189`); no switch to turn it off.

**Assessment** — *adapt*: useful for agents talking to a node, but it should
expose an explicit, minimal set of tools rather than the whole API.

### 14. Metrics / heartbeat

**Facts** — Documented in [federation-and-metrics.md](federation-and-metrics.md#2-metrics):
an unauthenticated POST at startup and every 55 minutes, one per Endpoint
from the leader worker since 0.34.38, with no stable identifier, no schema
version and string-formatted measurements.

**Assessment** — *adapt*. This is the closest thing to the heartbeat a control
plane needs, and the obvious first piece of a connector node, but the
contract needs an identity, a schema version and typed values first (the
status/heartbeat contract in PASS-101).

### 15. Affinities client

**Facts** — Registers datasets and services and their links in Affinities
(`api/services/affinities_services/affinities_client.py`), no auth headers,
enabled only when `AFFINITIES_ENABLED`, `AFFINITIES_URL` and
`AFFINITIES_EP_UUID` are all set; the installer always disables it
(`install/install.sh:1039`).

**Assessment** — *as-is* technically; whether a connector node registers in
Affinities is a product question.

### 16. Access requests

**Facts** — Self-service requests stored in MongoDB, approved by an admin
through AAI group/role calls made with the admin's own token. Since 0.34.46
the group is the first `GROUP_NAMES` entry (on a registered install,
`ndp_ep/ep-<config-id>`), falling back to `AFFINITIES_EP_UUID` only when
there is none; with neither, approval answers 503
(`api/services/access_request_services/access_request_service.py:63-88`,
`142-171`).

**Assessment** — *not applicable*: user management belongs to the full
Endpoint or to the platform.

### 17. Web UI

**Facts** — React app built into the image and served by nginx at
`${ROOT_PATH}/ui/` (`ROOT_PATH` is empty by default); runtime settings
injected by `entrypoint.sh`.

**Assessment** — *not applicable* for a minimal node.

### 18. Installer and Federation bootstrap

**Facts** — `install/install.sh` registers with the Federation
(`POST /ep/simple`), bootstraps from a config id (`GET /ep/{id}`), renders
`.env` from `example.env` and starts the compose stack; see
[federation-and-metrics.md](federation-and-metrics.md#1-registration-and-configuration).

**Assessment** — *adapt*. The config-id bootstrap ("register once in the
Federation, install anywhere with one id") is exactly the flow a connector
node needs; the script itself is tied to this compose stack.

### 19. Packaging

**Facts** — One image (`Dockerfile.allinone`: React build + Python + nginx +
supervisord) and compose profiles `mongodb`, `s3`, `kafka`, `mongo-express`,
`jupyter`, `pelican` and `full` (`docker-compose.yml`). The `api` service has
no published image: compose builds it from the checkout, and the installer
runs `up -d --build` (`install/install.sh:1531`).

**Assessment** — *adapt*: a connector node would want a smaller image without
the UI and nginx, and a published image rather than a local build.

## What a minimal profile looks like today

**Fact** — These settings already produce the smallest Endpoint the code
allows:

```env
LOCAL_CATALOG_BACKEND=none
CKAN_LOCAL_ENABLED=False
S3_ENABLED=False
KAFKA_CONNECTION=False
PELICAN_ENABLED=False
USE_JUPYTERLAB=False
REXEC_CONNECTION=False
AFFINITIES_ENABLED=False
ENABLE_ACCESS_REQUESTS=False
OIDC_ENABLED=False
```

What still runs: the API with health, search, status, user and
service-redirect routes, the MCP server, the metrics loop, authentication, and
the UI.

**Assessment** — that profile is a read-only Endpoint: it exposes nothing
local. Which exposure mechanisms a connector node needs depends on Q5.

## Open questions the connector-node definition must answer

1. **What does a connector node expose?** Catalog metadata, files (S3 /
   Pelican), live services (proxy), streams, or a subset — and is that a
   per-node choice? (Q5)
2. **Who is the node's identity?** Today an Endpoint has no stable identifier
   of its own (federation-and-metrics.md, gap 4.4). Does a node get a
   Federation-issued id and credential, and who issues the token it presents?
   (Q16)
3. **Does it hold a catalog**, or only push descriptions to a central one?
4. **Where do its secrets live?** Today staging-catalog keys travel through
   the Federation configuration and end up in `.env`. (Q9)
5. **How is it reached?** Public HTTPS like an Endpoint, or a private network
   (NetBird)? (Q1)
6. **What is the heartbeat contract** — identity, schema version, typed
   values, interval, authentication? (PASS-101)
7. **How is it deployed and updated** — the same installer and config-id
   bootstrap, a published image, or an agent?
