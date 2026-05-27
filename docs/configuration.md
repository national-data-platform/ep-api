# Configuration reference (`.env`)

NDP-EP is configured entirely through environment variables, normally placed in
a `.env` file next to `docker-compose.yml`. The annotated template is
[`example.env`](../example.env) — copy it to `.env` and edit.

This page explains **every** variable: what it is, what it controls, where to get
its value, and whether you need it. Booleans are `True` / `False`.

- **Required** = the Endpoint will not work correctly without it for the feature it
  controls.
- **Optional** = safe to leave at its default.
- Unknown variables are ignored (settings allow extras), so a shared `.env` across
  components is fine.

### Minimum to get started (connect to the National Data Platform)

You really only need to set:

- `AUTH_API_URL` → the platform's AAI (so logins/roles work).
- `LOCAL_CATALOG_BACKEND` + its backend vars (`MONGODB_*` **or** `CKAN_*`) → where this EP stores its catalog.
- `CKAN_LOCAL_ENABLED=True` → if this EP should allow publishing (not read-only).
- `ORGANIZATION`, `EP_NAME` → how your EP identifies itself.

Everything else turns optional features on/off.

---

## General / API

#### `ROOT_PATH`
*Optional · default: empty (served at `/`).*
URL path prefix when the EP runs behind a reverse proxy at a sub-path (e.g.
`/ep-api`). It makes the API and UI build correct links. **Where:** match the path
your reverse proxy mounts the EP at; leave empty if it is served at the domain root.

#### `ORGANIZATION`
*Optional · default: `Unknown Organization`.*
Display name of the organization running this Endpoint (shown in the UI and
reported to Federation). **Where:** you choose it.

#### `EP_NAME`
*Optional · default: `Unknown EP`.*
Display name of this Endpoint (UI + Federation registry). **Where:** you choose it.

#### `IS_PUBLIC`
*Optional · default: `True`.*
Whether this Endpoint advertises itself as public. **Where:** set `False` for a
private/internal EP.

#### `USE_JUPYTERLAB` / `JUPYTER_URL`
*Optional · defaults: `False` / `https://jupyter.org/try-jupyter/lab/`.*
Show a "JupyterLab" link in the UI and where it points. **Where:** set `USE_JUPYTERLAB=True`
and `JUPYTER_URL` to your JupyterLab instance if you offer one.

#### `SWAGGER_TITLE` / `SWAGGER_DESCRIPTION` / `SWAGGER_VERSION`
*Advanced · usually leave default.*
Metadata shown on the `/docs` (Swagger) page. `SWAGGER_VERSION` tracks the release
and normally should not be overridden.

---

## Authentication & access (AAI)

#### `AUTH_API_URL`
*Required · default: `https://idp.nationaldataplatform.org/temp/information`.*
The AAI endpoint the EP calls to **validate bearer tokens** and read the user's
identity, groups and **roles**. This is the single source of authentication.
**Where:** your NDP/AAI administrator. For the central platform use the default;
for a self-hosted AAI use its `…/information` URL.

#### `TEST_TOKEN`
*Optional · dev only · default: `testing_token`.*
A fixed token the EP accepts without contacting AAI, for local testing.
**Where:** you set it for dev. **Leave blank in production.**

#### `ENABLE_GROUP_BASED_ACCESS`
*Optional · default: `False`.*
If `True`, write operations (POST/PUT/DELETE) additionally require the user to
belong to one of `GROUP_NAMES`. This is an extra gate on top of the role model.
**Where:** enable only if you want group-scoped writes.

#### `GROUP_NAMES`
*Optional · default: empty.*
Comma-separated list of groups allowed to write when `ENABLE_GROUP_BASED_ACCESS=True`
(e.g. `admins,data-managers`). Matching is case-insensitive; empty + enabled =
all writes denied. **Where:** the group names defined in Keycloak/AAI — ask your
AAI administrator.

> **Roles** (`viewer` / `writer` / `admin`) are **not** set here — they travel in
> the token issued by AAI. See [roles-and-permissions.md](roles-and-permissions.md).

---

## Local catalog (where this EP stores its data)

#### `LOCAL_CATALOG_BACKEND`
*Required · default: `ckan`.*
Backend for **this EP's own** catalog: `ckan` or `mongodb`. (The global and
Pre-CKAN catalogs always use CKAN regardless.) **Where:** you choose — `mongodb`
is the simplest to self-host; `ckan` if you already run a CKAN.

#### `CKAN_LOCAL_ENABLED`
*Optional · default: `False`.*
Master switch for **write** operations on the local catalog (create/update/delete
organizations, datasets, resources), for **any** backend. `False` makes the EP
read-only. *(The name keeps "CKAN" for historical reasons; it applies to MongoDB
too.)* **Where:** set `True` if this EP should accept publishing.

### CKAN backend — only if `LOCAL_CATALOG_BACKEND=ckan`

#### `CKAN_URL`
*Required (CKAN backend) · default: `http://localhost:5000`.*
Base URL of your CKAN instance. **Where:** your CKAN deployment URL.

#### `CKAN_API_KEY`
*Required (CKAN backend).*
API key used to write to CKAN. **Where:** in CKAN, log in → your user profile →
**API Tokens** → create a token.

#### `CKAN_VERIFY_SSL`
*Optional · default: `True`.*
Verify CKAN's TLS certificate. **Where:** set `False` only for self-signed/dev
CKAN instances (less secure).

#### `CKAN_GLOBAL_URL`
*Optional · default: `https://nationaldataplatform.org/catalog`.*
Read-only global NDP catalog the EP can search alongside the local one.
**Where:** usually leave the default.

### MongoDB backend — only if `LOCAL_CATALOG_BACKEND=mongodb`

#### `MONGODB_CONNECTION_STRING`
*Required (MongoDB backend) · default: `mongodb://localhost:27017`.*
MongoDB connection URI for the local catalog. **Where:** your MongoDB. With the
bundled Compose (`--profile mongodb`) use `mongodb://admin:admin123@mongodb:27017`.

#### `MONGODB_DATABASE`
*Optional · default: `ndp_local_catalog`.*
Database name used for the local catalog. **Where:** you choose.

### Pre-CKAN (optional staging catalog)

#### `PRE_CKAN_ENABLED`
*Optional · default: `False`.*
Enable a Pre-CKAN staging target (publish to a review instance before the global
catalog).

#### `PRE_CKAN_URL` / `PRE_CKAN_API_KEY` / `PRE_CKAN_VERIFY_SSL` / `PRE_CKAN_ORGANIZATION`
*Required only if `PRE_CKAN_ENABLED=True`.*
URL, API key (same place as `CKAN_API_KEY`, but on the Pre-CKAN instance), TLS
verification, and the organization all staged datasets are published under
(overrides their `owner_org`). **Where:** from whoever operates your Pre-CKAN
(e.g. the SDSC staging instance).

---

## S3 / object storage (MinIO)

#### `S3_ENABLED`
*Optional · default: `False`.*
Enable S3 object storage and the **S3 Management** tool in the UI (writers only).

#### `S3_ENDPOINT`
*Required if `S3_ENABLED=True` · default: `localhost:9000`.*
`host:port` of the S3-compatible service. **Where:** your MinIO/S3 endpoint. With
the bundled Compose (`--profile s3`) use `minio:9000`.

#### `S3_ACCESS_KEY` / `S3_SECRET_KEY`
*Required if `S3_ENABLED=True` · dev defaults: `minioadmin` / `minioadmin123`.*
Credentials for the S3 service. **Where:** your MinIO/S3 admin console (Access
Keys). The dev MinIO ships with `minioadmin` / `minioadmin123`.

#### `S3_SECURE`
*Optional · default: `False`.*
`True` for HTTPS, `False` for HTTP. **Where:** `True` when your S3 endpoint serves
TLS.

#### `S3_REGION`
*Optional · default: `us-east-1`.*
Region label sent to the S3 API. **Where:** match your provider; the default is
fine for MinIO.

---

## Streaming (Kafka)

#### `KAFKA_CONNECTION`
*Optional · default: `False`.*
Enable Kafka connectivity (managing/streaming topics).

#### `KAFKA_HOST` / `KAFKA_PORT`
*Required if `KAFKA_CONNECTION=True` · defaults: `localhost` / `9092`.*
Kafka broker address. **Where:** your broker. With the bundled Compose
(`--profile kafka`) use `kafka` and `9093` (internal) / `9092` (external).

#### `KAFKA_PREFIX`
*Optional · default: `data_stream_`.*
Prefix applied to topics the EP manages. **Where:** you choose.

#### `MAX_STREAMS`
*Optional · default: `10`.*
Maximum number of concurrent managed streams.

---

## Affinities integration

#### `AFFINITIES_ENABLED`
*Optional · default: `False`.*
When `True`, datasets/services created here are auto-registered in Affinities
(non-blocking — the EP keeps working if Affinities is down).

#### `AFFINITIES_URL`
*Required if `AFFINITIES_ENABLED=True`.*
Base URL of the Affinities API (e.g. `http://affinities-api:8000`). **Where:** the
platform's Affinities URL, or your local one.

#### `AFFINITIES_EP_UUID`
*Required if `AFFINITIES_ENABLED=True`.*
This Endpoint's UUID inside Affinities. **Where:** register the Endpoint once via
`POST /endpoints` on the Affinities API; the response's `uid` is this value. See
[affinities-integration.md](affinities-integration.md).

#### `AFFINITIES_TIMEOUT`
*Optional · default: `30`.*
HTTP timeout (seconds) for Affinities calls.

---

## Federation (metrics reporting)

#### `METRICS_ENDPOINT`
*Optional · default: `https://federation.ndp.utah.edu/metrics/`.*
The Federation endpoint this EP periodically reports health/usage metrics to,
which is how the EP becomes discoverable in the federation. **Where:** the
platform's Federation `/metrics/` URL, or your local Federation when self-hosting.

#### `METRICS_INTERVAL_SECONDS`
*Optional · default: `3300` (55 min).*
How often metrics are reported.

---

## Pelican federation (external data access)

#### `PELICAN_ENABLED`
*Optional · default: `False`.*
Enable browsing/downloading from Pelican federations (OSDF, etc.) and support for
`pelican://` resource URLs.

#### `PELICAN_FEDERATION_URL`
*Optional · default: empty (uses OSDF).*
Default Pelican federation, format `pelican://host` (e.g. `pelican://osg-htc.org`).
**Where:** the federation you target; leave empty for OSDF.

#### `PELICAN_DIRECT_READS`
*Optional · default: `False`.*
Read straight from origin servers instead of caches. **Where:** keep `False` for
better performance unless you have a reason.

---

## Remote execution (Rexec)

#### `REXEC_CONNECTION`
*Optional · default: `False`.*
Enable the Remote Execution Deployment API integration.

#### `REXEC_DEPLOYMENT_API_URL`
*Required if `REXEC_CONNECTION=True`.*
URL of the Remote Execution Deployment API. **Where:** from whoever operates that
service.

---

## Access requests

#### `ENABLE_ACCESS_REQUESTS`
*Optional · default: `False`.*
Enable the access-request workflow (a user requests access; an admin
approves/rejects). **Requires MongoDB** reachable via `MONGODB_CONNECTION_STRING`.
**Where:** turn on if you want self-service access requests.

#### `ACCESS_REQUESTS_COLLECTION`
*Optional · default: `access_requests`.*
MongoDB collection used to store access requests.

---

## Telemetry — OpenTelemetry (advanced)

#### `OTEL_ENABLED`
*Optional · default: `False`.* Enable OpenTelemetry tracing.

#### `OTEL_SERVICE_NAME`
*Optional · default: `ep-api`.* Service name shown in traces.

#### `OTEL_EXPORTER_TYPE`
*Optional · default: `console`.* Where traces go: `console`, `otlp`, or `none`.

#### `OTEL_OTLP_ENDPOINT`
*Optional · default: `http://localhost:4317`.* OTLP collector endpoint (when
`OTEL_EXPORTER_TYPE=otlp`). **Where:** your collector's address.

#### `OTEL_OTLP_INSECURE`
*Optional · default: `True`.* Use a non-TLS OTLP connection.

---

> **Tip:** start from [`example.env`](../example.env) and override only what your
> deployment needs. When in doubt about a value for a shared platform service
> (AAI, Affinities, Federation), ask your NDP administrator.
