# Configuration reference (`.env`)

All NDP-EP configuration is provided through environment variables (usually in a
`.env` file). The canonical template is [`example.env`](../example.env) in the
repository root — copy it to `.env` and adjust. This page explains every
variable, grouped by area.

Booleans are `True` / `False`. Values shown under *Default* are the built-in
defaults; the `example.env` template may ship different example values.

---

## General / API

| Variable | Default | Description |
|---|---|---|
| `ROOT_PATH` | *(empty)* | URL path prefix when served behind a reverse proxy at a subpath (e.g. `/ep-api`). Empty = served at root. |
| `ORGANIZATION` | `Unknown Organization` | Display name of the organization that runs this Endpoint. |
| `EP_NAME` | `Unknown EP` | Display name of this Endpoint. |
| `IS_PUBLIC` | `True` | Whether the Endpoint presents itself as public. |
| `USE_JUPYTERLAB` | `False` | Show a JupyterLab integration link in the UI. |
| `JUPYTER_URL` | `https://jupyter.org/try-jupyter/lab/` | URL of the JupyterLab instance to link to. |

## Authentication & access (AAI)

| Variable | Default | Description |
|---|---|---|
| `AUTH_API_URL` | `https://idp.nationaldataplatform.org/temp/information` | AAI endpoint used to validate bearer tokens and fetch user info (identity + **roles**). |
| `TEST_TOKEN` | `testing_token` | Optional test token for local development. Leave blank in production. |
| `ENABLE_GROUP_BASED_ACCESS` | `False` | If `True`, write operations require the user to belong to one of `GROUP_NAMES`. |
| `GROUP_NAMES` | *(empty)* | Comma-separated list of groups allowed to write (e.g. `admins,data-managers`). Empty + enabled = all writes denied. Matching is case-insensitive. |

> Roles (`viewer` / `writer` / `admin`) come from the **token issued by AAI**, not
> from this Endpoint. See [roles-and-permissions.md](roles-and-permissions.md).

## Local catalog

| Variable | Default | Description |
|---|---|---|
| `LOCAL_CATALOG_BACKEND` | `ckan` | Backend for the local catalog: `ckan` or `mongodb`. (Global / Pre-CKAN always use CKAN.) |
| `CKAN_LOCAL_ENABLED` | `False` | Enables write operations (POST/PUT/DELETE) on the local catalog, for **any** backend. `False` = read-only. *(Name keeps "CKAN" for historical reasons.)* |

### CKAN backend (`LOCAL_CATALOG_BACKEND=ckan`)

| Variable | Default | Description |
|---|---|---|
| `CKAN_URL` | `http://localhost:5000` | Base URL of the local CKAN instance. |
| `CKAN_API_KEY` | *(set me)* | API key for CKAN authentication. |
| `CKAN_VERIFY_SSL` | `True` | Verify the CKAN TLS certificate. Set `False` for self-signed dev instances. |
| `CKAN_GLOBAL_URL` | `https://nationaldataplatform.org/catalog` | URL of the global NDP catalog (read). |

### MongoDB backend (`LOCAL_CATALOG_BACKEND=mongodb`)

| Variable | Default | Description |
|---|---|---|
| `MONGODB_CONNECTION_STRING` | `mongodb://localhost:27017` | MongoDB connection string. In Compose use the `mongodb` service name. |
| `MONGODB_DATABASE` | `ndp_local_catalog` | Database name for the local catalog. |

### Pre-CKAN (staging)

| Variable | Default | Description |
|---|---|---|
| `PRE_CKAN_ENABLED` | `False` | Enable the Pre-CKAN staging instance. |
| `PRE_CKAN_URL` | *(empty)* | URL of the Pre-CKAN instance. |
| `PRE_CKAN_API_KEY` | *(empty)* | API key for Pre-CKAN. |
| `PRE_CKAN_VERIFY_SSL` | `True` | Verify the Pre-CKAN TLS certificate. |
| `PRE_CKAN_ORGANIZATION` | *(empty)* | Organization used for all datasets published to Pre-CKAN (overrides `owner_org`). |

## S3 / object storage (MinIO)

| Variable | Default | Description |
|---|---|---|
| `S3_ENABLED` | `False` | Enable S3 storage and the S3 Management tool. |
| `S3_ENDPOINT` | *(set me)* | S3-compatible endpoint `host:port` (Compose: `minio:9000`). |
| `S3_ACCESS_KEY` | *(set me)* | S3 access key. |
| `S3_SECRET_KEY` | *(set me)* | S3 secret key. |
| `S3_SECURE` | `False` | `True` for HTTPS, `False` for HTTP. |
| `S3_REGION` | `us-east-1` | Default S3 region. |

## Streaming (Kafka)

| Variable | Default | Description |
|---|---|---|
| `KAFKA_CONNECTION` | `False` | Enable Kafka connectivity. |
| `KAFKA_HOST` | `localhost` | Kafka broker host (Compose: `kafka`). |
| `KAFKA_PORT` | `9092` | Kafka broker port (internal Docker network often `9093`). |
| `KAFKA_PREFIX` | `data_stream_` | Prefix for managed Kafka topics. |
| `MAX_STREAMS` | `10` | Maximum number of streams. |

## Affinities integration

| Variable | Default | Description |
|---|---|---|
| `AFFINITIES_ENABLED` | `False` | Auto-register datasets/services in Affinities (non-blocking). |
| `AFFINITIES_URL` | *(empty)* | Base URL of the Affinities API. |
| `AFFINITIES_EP_UUID` | *(empty)* | This Endpoint's UUID in Affinities (from `POST /endpoints`). |
| `AFFINITIES_TIMEOUT` | `30` | Request timeout in seconds. |

See [affinities-integration.md](affinities-integration.md) for the full flow.

## Federation (metrics reporting)

| Variable | Default | Description |
|---|---|---|
| `METRICS_ENDPOINT` | `https://federation.ndp.utah.edu/metrics/` | Federation endpoint this EP reports metrics to. |
| `METRICS_INTERVAL_SECONDS` | `3300` | How often to report metrics (default 55 min). |

## Pelican federation

| Variable | Default | Description |
|---|---|---|
| `PELICAN_ENABLED` | `False` | Enable browsing/downloading from Pelican federations and `pelican://` URLs. |
| `PELICAN_FEDERATION_URL` | *(empty)* | Default Pelican federation (empty = OSDF). Format `pelican://host`. |
| `PELICAN_DIRECT_READS` | `False` | Read directly from origins (bypass caches). |

## Remote execution (Rexec)

| Variable | Default | Description |
|---|---|---|
| `REXEC_CONNECTION` | `False` | Enable the Remote Execution Deployment API integration. |
| `REXEC_DEPLOYMENT_API_URL` | *(empty)* | URL of the Remote Execution Deployment API. |

## Access requests

| Variable | Default | Description |
|---|---|---|
| `ENABLE_ACCESS_REQUESTS` | `False` | Enable the access-request workflow (admin-gated). |
| `ACCESS_REQUESTS_COLLECTION` | `access_requests` | Collection name used to store access requests. |

## Telemetry (OpenTelemetry, advanced)

| Variable | Default | Description |
|---|---|---|
| `OTEL_ENABLED` | `False` | Enable OpenTelemetry tracing. |
| `OTEL_SERVICE_NAME` | `ep-api` | Service name reported in traces. |
| `OTEL_EXPORTER_TYPE` | `console` | Exporter: `console`, `otlp`, or `none`. |
| `OTEL_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector endpoint. |
| `OTEL_OTLP_INSECURE` | `True` | Use an insecure (non-TLS) OTLP connection. |

---

> **Tip:** start from [`example.env`](../example.env), which contains these
> variables with inline comments, and override only what your deployment needs.
