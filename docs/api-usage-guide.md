# API usage guide

How to call the NDP Endpoint (EP) API with `curl`: authentication, the routes,
their bodies, what they return and how they fail. Every example was checked
against the route and model definitions in `api/routes/` and `api/models/` at
v0.34.45. The interactive reference for the running version is Swagger UI at
`/docs` (OpenAPI schema at `/openapi.json`).

## Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Which routes exist on an Endpoint](#which-routes-exist-on-an-endpoint)
- [The `server` parameter](#the-server-parameter)
- [Health and status](#health-and-status)
- [Organizations](#organizations)
- [Datasets](#datasets)
- [URL, S3 and Kafka datasets](#url-s3-and-kafka-datasets)
- [Services](#services)
- [Search](#search)
- [Resources](#resources)
- [Deleting](#deleting)
- [S3 buckets and objects](#s3-buckets-and-objects)
- [Pelican](#pelican)
- [Access requests](#access-requests)
- [Errors](#errors)

---

## Base URL

```bash
EP=http://localhost:8002          # EP_API_PORT, default 8002
TOKEN=<your access token>
```

The container's nginx serves the API at `${ROOT_PATH}/` and, as an alias, at
`${ROOT_PATH}/api/`; the UI is at `${ROOT_PATH}/ui/`. With `ROOT_PATH=/ep`, use
`EP=http://localhost:8002/ep`. A route requested without the trailing slash it
is declared with (for example `/status` or `/s3/buckets`) answers 307 to the
slashed path; `curl -L` follows it.

`GET /` answers `"API is running successfully."`. The same app also serves an
MCP server at `/mcp` exposing the routes in the OpenAPI schema (see
[architecture/overview.md](architecture/overview.md#mcp)).

---

## Authentication

Send an access token issued by the platform's identity provider:

```bash
curl -s "$EP/user/info" -H "Authorization: Bearer $TOKEN"
```

The Endpoint validates the token on every request by posting it to
`AUTH_API_URL`. To obtain a token with a username and password:

```bash
curl -s -X POST "$EP/user/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "<user>", "password": "<password>"}'
```

The response is the identity provider's, including `access_token`. `POST /token`
accepts the same credentials as form fields (`username`, `password`) for older
clients.

`TEST_TOKEN` (default `testing_token`) is accepted without contacting the
identity provider and acts as a platform administrator. It is meant for local
development and should be blank anywhere else; the examples below use
`$TOKEN` for either.

### `GET /user/info`

Returns the identity provider's payload plus `ndp_user_id` and
`effective_role`. With the test token:

```json
{
  "roles": ["ndp_admin"],
  "groups": [],
  "sub": "test_user",
  "username": "Test User",
  "ndp_user_id": "1160130875fda081",
  "effective_role": "admin"
}
```

A real user's payload carries whatever the identity provider returns (`email`
and others). `effective_role` is `admin`, `writer`, `viewer` or `none`;
`ndp_user_id` is the first 16 hex characters of SHA-256 of `sub`, the same
value stored in the `ndp_user_id` extra of datasets the user creates. With
`ENABLE_GROUP_BASED_ACCESS=True`, a user outside the Endpoint's groups gets 403
here.

### Who may call what

| Requirement | Routes |
|---|---|
| No token | `GET /`, `/health`, `/ready`, `GET /search`, `POST /search`, `GET /organization` (except `mine=true`), `GET /resource/{id}`, `GET /resources/search`, `POST /user/login`, `POST /token`, the service proxy unless the service sets `requires_auth` |
| Any valid token | `/status/*` (except `/status/rexec`), `POST /user/access-requests`, `GET /organization?mine=true` |
| Group gate only | `GET /user/info` |
| viewer | `/pelican/*` |
| writer | every POST/PUT/PATCH/DELETE on the catalog, `POST /dataset/{id}/publish`, every `/s3/buckets` and `/s3/objects` route (GETs included), `/status/rexec`, `POST /pelican/import-metadata` |
| admin | `GET /user/access-requests`, approve, reject |

"Group gate" applies only with `ENABLE_GROUP_BASED_ACCESS=True`, and also
applies to every viewer and writer route. Details in
[roles-and-permissions.md](roles-and-permissions.md).

---

## Which routes exist on an Endpoint

Some route groups are mounted only when a feature is on, so on another
Endpoint they may answer 404:

| Routes | Mounted when |
|---|---|
| Registration, update, delete and resource routes | `CKAN_LOCAL_ENABLED=True` and `LOCAL_CATALOG_BACKEND` is not `none` |
| `/s3/buckets/…`, `/s3/objects/…` | `S3_ENABLED=True` |
| `/pelican/…` | `PELICAN_ENABLED=True` |
| `/status/jupyter` | `USE_JUPYTERLAB=True` |
| `/status/rexec` | `REXEC_CONNECTION=True` |

`GET /status/` tells a client which features are on.

---

## The `server` parameter

Many routes take `?server=` to choose a catalog. The accepted values and
the default differ per route:

| Route | Accepted | Default |
|---|---|---|
| `GET /search` | `local`, `global` | `global` |
| `POST /search` (in the body) | `local`, `global`, `pre_ckan` | `global` |
| `GET /organization` | `local`, `global`, `pre_ckan` | `global` |
| `POST /organization`, `/dataset`, `/url`, `/s3`, `/kafka`, `/services` | `local`, `pre_ckan` | `local` |
| `PUT`/`PATCH` `/dataset/{id}`, `/url/{id}`, `/s3/{id}`, `/kafka/{id}`, `/services/{id}` | `local`, `pre_ckan` | `local` |
| `GET`/`PATCH /resource/{id}`, `GET /resources/search`, `PATCH`/`DELETE /dataset/{id}/resource/{rid}`, `DELETE /resource…` | `local`, `pre_ckan` | `local` |
| `DELETE /organization/{name}` | `local` | `local` |

- `local` is this Endpoint's catalog (CKAN or MongoDB, per
  `LOCAL_CATALOG_BACKEND`). `GET /search?server=local` answers 400 when
  `CKAN_LOCAL_ENABLED` is false.
- `global` is the NDP catalog at `CKAN_GLOBAL_URL`, read-only.
- `pre_ckan` is the staging catalog; any route answers 400
  `Pre-CKAN is disabled and cannot be used.` when `PRE_CKAN_ENABLED` is false.
- Any other value fails validation with 422.

---

## Health and status

```bash
curl -s "$EP/health"        # {"status": "healthy", "timestamp": "...Z"}
curl -s "$EP/ready"         # 200 healthy / 503 unhealthy, with per-dependency checks
curl -s "$EP/status/" -H "Authorization: Bearer $TOKEN"
```

`GET /ready`:

```json
{
  "status": "healthy",
  "timestamp": "2026-10-08T12:00:00.000000Z",
  "checks": {
    "local_catalog": {"status": "up", "latency_ms": 3.1, "backend": "mongodb"},
    "pre_ckan": {"status": "disabled"},
    "minio": {"status": "up", "latency_ms": 5.0},
    "kafka": {"status": "disabled"},
    "affinities": {"status": "disabled"}
  }
}
```

It answers 503 when any enabled check other than `affinities` is `down`.

`GET /status/` always contains `api_version`, `organization`, `ep_name`,
`group_based_access`, `local_catalog_backend`, `backend_connected`,
`pre_ckan_enabled`, `kafka_enabled`, `jupyterlab_enabled`, `s3_enabled`,
`access_requests_enabled`, `auth_api_url`, `metrics_endpoint`,
`metrics_interval_seconds` and `is_public`; plus `pre_ckan_connected`,
`kafka_host`/`kafka_port`, `jupyterlab_url` and `s3_connected` when the
corresponding feature is on.

Other status routes (token required): `GET /status/metrics` (system metrics
and service status), `GET /status/kafka-details` (`kafka_host`, `kafka_port`,
`kafka_connection`, `kafka_prefix`, `max_streams`), `GET /status/jupyter`
(`jupyter_url`), `GET /status/rexec` (`deployment_api_url`, writer role).

---

## Organizations

### List

```bash
curl -s "$EP/organization"                          # global catalog
curl -s "$EP/organization?server=local&name=rese"   # local, name contains "rese"
curl -s "$EP/organization?server=local&mine=true" -H "Authorization: Bearer $TOKEN"
```

Returns a list of organization names, e.g. `["services", "research_team"]`.
`mine=true` keeps only organizations created by the caller and requires a
token (401 without one); organizations created before creator attribution was
recorded are never included.

### Create — writer

```bash
curl -s -X POST "$EP/organization" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "research_team", "title": "Research Team",
       "description": "Organization for research projects"}'
```

`201`:

```json
{"id": "911f00d5-8e99-4d92-9187-5cb8d011c19b", "message": "Organization created successfully"}
```

`name` and `title` are required, `description` optional. Any failure,
including a duplicate name, is a 400 carrying the backend's message.

Deleting an organization is under [Deleting](#deleting).

---

## Datasets

### Create — `POST /dataset`, writer

```bash
curl -s -X POST "$EP/dataset" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "name": "climate_research_2024",
    "title": "Climate Research Dataset 2024",
    "owner_org": "research_team",
    "notes": "Climate data from the 2024 field campaign",
    "tags": ["climate", "research"],
    "extras": {"project": "climate_study"},
    "resources": [
      {"url": "https://data.example.org/obs.csv", "name": "observations",
       "format": "CSV", "description": "Daily observations"}
    ],
    "private": false,
    "license_id": "cc-by",
    "version": "1.0"
  }'
```

Body ([`GeneralDatasetRequest`](../api/models/general_dataset_request_model.py)):

| Field | Required | Notes |
|---|---|---|
| `name` | yes | `^[a-z0-9_-]+$` |
| `title` | yes | |
| `owner_org` | yes | Organization name or id; it must exist. |
| `notes`, `tags`, `groups`, `extras`, `license_id`, `version` | no | `tags` and `groups` are lists of names. |
| `private` | no | Default `false`. |
| `resources` | no | Each `{url, name, format?, description?, mimetype?, size?}`; `url` must start with `http://`, `https://`, `s3://`, `ws://`, `wss://`, `/` or `.`. |

`201`:

```json
{
  "id": "cf248952-0f9d-4abe-8df2-fbae0b699f4d",
  "name": "climate_research_2024",
  "title": "Climate Research Dataset 2024",
  "warning": null
}
```

**Duplicate names.** When a CKAN catalog (local CKAN or Pre-CKAN) reports the
name or URL as already in use, the dataset is created again with a timestamp
suffix and the response explains it:

```json
{
  "id": "…",
  "name": "climate_research_2024-20261008143052",
  "title": "Climate Research Dataset 2024 (2026-10-08 14:30:52)",
  "warning": "A dataset named 'climate_research_2024' already exists. This dataset was saved as 'climate_research_2024-20261008143052' with title 'Climate Research Dataset 2024 (2026-10-08 14:30:52)'."
}
```

The MongoDB backend reports duplicates with a different message, so on a
MongoDB catalog a duplicate name is a 400
(`Error creating dataset: … Package with name '…' already exists`) and nothing
is renamed.

**Extras.** These keys are reserved and answer 400 (`Reserved key error: …`)
when sent in `extras`: `name`, `title`, `owner_org`, `notes`, `id`,
`resources`, `tags`, `private`, `license_id`, `version`, `state`, `created`,
`last_modified`, `url` (`RESERVED_KEYS` in
[`general_dataset.py`](../api/services/dataset_services/general_dataset.py)).
The Endpoint adds `ndp_group_id` (`ORGANIZATION`), `ndp_user_id` and
`ndp_creator_md5` (MD5 of the caller's `sub`) to every new dataset,
overwriting any value sent for them; updates keep the stored values and
silently ignore new ones. With the Affinities integration on, the dataset
also gets `ndp_affinity_uuid`
([affinities-integration.md](affinities-integration.md)).

### Update — `PUT /dataset/{id}` and `PATCH /dataset/{id}`, writer

Both take the same body with every field optional
([`GeneralDatasetUpdateRequest`](../api/models/general_dataset_request_model.py))
and answer `{"message": "Dataset updated successfully"}`. Fields left out keep
their stored values in both. They differ in two things:

- `resources`: `PUT` replaces the whole list; `PATCH` updates the resources
  whose `url` or `name` matches and appends the others.
- `extras`: both merge into the stored extras (the `ndp_*` identity keys are
  kept).

```bash
curl -s -X PATCH "$EP/dataset/climate_research_2024" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"notes": "Updated description", "tags": ["climate", "2024"]}'
```

`{id}` may be the dataset id or name.

### Publish to Pre-CKAN — `POST /dataset/{id}/publish`, writer

Copies a local dataset (by id or name) and its resources to the staging
catalog. Requires `PRE_CKAN_ENABLED`. `201`:

```json
{"id": "…", "name": "…", "title": "…", "warning": null,
 "message": "Dataset published to PRE-CKAN successfully"}
```

The same duplicate-name renaming applies. The dataset is created under
`PRE_CKAN_ORGANIZATION` when that is set. A dataset that does not exist
locally is 404; the staging catalog refusing the credentials is 403, refusing
the content is 400, and any other failure there is 502. The full flow is in
[sequence-diagrams/publishing-a-dataset.md](sequence-diagrams/publishing-a-dataset.md).

---

## URL, S3 and Kafka datasets

These routes create a dataset with one resource of a given kind. They answer
`201 {"id": "<dataset id>"}`.

### `POST /url` — writer

```bash
curl -s -X POST "$EP/url" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "resource_name": "temperature_data",
    "resource_title": "Temperature Dataset",
    "owner_org": "research_team",
    "resource_url": "https://data.example.org/temperature.csv",
    "file_type": "CSV",
    "notes": "Daily temperature readings",
    "processing": {"delimiter": ",", "header_line": 1, "start_line": 2}
  }'
```

`resource_name` follows `^[a-z0-9_-]+$`; `resource_url` must start with
`http://` or `https://`. `file_type` is free text; for `stream`, `CSV`, `TXT`,
`JSON` and `NetCDF` the `processing` object is validated against that type's
fields (`refresh_rate`/`data_key`; `delimiter`/`header_line`/`start_line`/`comment_char`;
`delimiter`/`header_line`/`start_line`; `info_key`/`additional_key`/`data_key`;
`group`). `extras` and `mapping` are string-to-string objects.

### `POST /s3` — writer

Registers a catalog dataset pointing at an object in S3. It does not touch the
S3 service and works without `S3_ENABLED`.

```bash
curl -s -X POST "$EP/s3" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "resource_name": "satellite_images",
    "resource_title": "Satellite Image Archive",
    "owner_org": "research_team",
    "resource_s3": "s3://research-data/satellite/2024/",
    "notes": "Satellite imagery for 2024",
    "extras": {"instrument": "MODIS"}
  }'
```

`resource_s3` must start with `s3://`, `http://` or `https://`.

### `POST /kafka` — writer

Registers a dataset describing a Kafka topic; nothing is created in Kafka.

```bash
curl -s -X POST "$EP/kafka" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "sensor_stream",
    "dataset_title": "Sensor Data Stream",
    "owner_org": "research_team",
    "kafka_topic": "sensors.temperature",
    "kafka_host": "kafka",
    "kafka_port": 9093,
    "dataset_description": "Real-time sensor data",
    "mapping": {"timestamp": "event_time", "value": "temperature"},
    "processing": {"data_key": "data", "info_key": "metadata"}
  }'
```

`kafka_port` is an integer from 1 to 65535. A name already in use is 409 with
`detail: {"error": "Duplicate Dataset", "detail": "…"}`.

### Updating them

`PUT` and `PATCH` on `/url/{id}`, `/s3/{id}` and `/kafka/{id}` take the same
fields, all optional, and answer `{"message": "…updated successfully"}`
(`PATCH /url/{id}` returns the service's result instead). With `server=local`
they change the configured local catalog, CKAN or MongoDB (since 0.34.48). A
new `resource_url` or `resource_s3` replaces the URL of the dataset's URL or S3
resource (for `resource_s3`, since 0.34.49).

---

## Services

A service is a dataset in the `services` organization (created at startup on
an Endpoint with a local catalog) whose resource is the service URL.

### `POST /services` — writer

```bash
curl -s -X POST "$EP/services" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "service_name": "weather_api",
    "service_title": "Weather API Service",
    "owner_org": "services",
    "service_url": "https://api.weather.example.org",
    "service_type": "API",
    "notes": "Real-time and forecast weather data",
    "health_check_url": "https://api.weather.example.org/health",
    "documentation_url": "https://api.weather.example.org/docs"
  }'
```

`owner_org` must be `services` (400 otherwise). `service_type` is free text up
to 50 characters; the UI offers `API`, `UI` and `Trigger`. `201 {"id": "…"}`;
a duplicate is 409 with `detail: {"error": "Duplicate Service", …}`.
`PUT`/`PATCH /services/{id}` take the same fields, all optional.

### Reaching a service through the Endpoint

```bash
curl -s "$EP/services/redirect/weather_api/v1/forecast?city=SLC"
```

`/services/redirect/{service_name}[/{path}]` looks the service up by name in
the local catalog and forwards the request (GET, POST, PUT, PATCH or DELETE,
with query, body and most headers) to its URL. No token is needed unless the
service has the extra `requires_auth` set to a true value (`true`, `1`, `yes`,
`on`), in which case a valid token is required. Unknown service: 404; target
unreachable: 502; target timeout: 504. Swagger lists these paths as
documentation-only entries.

---

## Search

### `GET /search` — by terms

```bash
curl -s "$EP/search?terms=climate&terms=temperature"
curl -s "$EP/search?terms=climate&keys=title&server=local"
```

- `terms` is required and repeatable. Each term is matched against the whole
  dataset; a dataset is returned only if every term appears in it.
- `keys` (optional, repeatable) gives one field per term, in order; `null`
  searches all fields for that term. Its length must equal `terms`' (400
  otherwise).
- `server`: `global` (default) or `local`.

### `POST /search` — by fields

```bash
curl -s -X POST "$EP/search" -H "Content-Type: application/json" \
  -d '{"owner_org": "services", "server": "local"}'

curl -s -X POST "$EP/search" -H "Content-Type: application/json" \
  -d '{"search_term": "weather,forecast", "server": "local"}'
```

Body fields ([`SearchRequest`](../api/models/searchrequest_model.py)), all
optional: `dataset_name`, `dataset_title`, `owner_org`, `dataset_description`,
`resource_url`, `resource_name`, `resource_description`, `resource_format`,
`search_term` (comma-separated keywords; a dataset must match all of them),
`filter_list` (list of `field:value`), `timestamp` (a value or range on the
`timestamp` field) and `server` (`local`, `global` — the default — or
`pre_ckan`). When `search_term` is given, `dataset_name`, `dataset_title`,
`owner_org` and `dataset_description` are ignored.

### Response

Both return a list of datasets:

```json
[
  {
    "id": "cf248952-0f9d-4abe-8df2-fbae0b699f4d",
    "name": "climate_research_2024",
    "title": "Climate Research Dataset 2024",
    "owner_org": "research_team",
    "notes": "Climate data from the 2024 field campaign",
    "resources": [
      {"id": "5b19…", "url": "https://data.example.org/obs.csv",
       "name": "observations", "description": "Daily observations", "format": "CSV"}
    ],
    "extras": {"project": "climate_study", "ndp_user_id": "…"}
  }
]
```

For `GET /search`, a catalog that cannot be reached answers 503 and a timeout
504. `POST /search` reports every failure, unreachable catalogs included, as
400 with the underlying message. `owner_org` in the results is the
organization's name.

---

## Resources

All on the catalog chosen by `server` (default `local`).

```bash
# One resource by id (no token)
curl -s "$EP/resource/<resource_id>"

# Search resources across datasets (no token)
curl -s "$EP/resources/search?format=CSV&name=obs&limit=50&offset=0"

# Update a resource — writer
curl -s -X PATCH "$EP/resource/<resource_id>" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"description": "Updated description", "format": "CSV"}'

# The same, addressed through its dataset — writer
curl -s -X PATCH "$EP/dataset/<dataset_id>/resource/<resource_id>" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "observations-v2"}'
```

`GET /resources/search` accepts `q` (matches name, URL or description), `name`,
`url`, `description` (partial matches), `format` (exact, case-insensitive),
`limit` (1–1000, default 100) and `offset`, and returns
`{"count": n, "results": [...]}` where each resource also carries
`dataset_id`, `dataset_name` and `dataset_title`. The PATCH body accepts
`name`, `url`, `description` and `format`.

---

## Deleting

All require the writer role, answer 200 with a `message`, and 404 when the
target does not exist.

| Route | Deletes |
|---|---|
| `DELETE /resource?resource_id=<id>` | The **dataset** with that id (the name is historical). |
| `DELETE /resource/{name}` | The **dataset** with that name. |
| `DELETE /dataset/{id}/resource/{rid}` | One resource; the dataset and its other resources stay. |
| `DELETE /organization/{name}?cascade=true` | The organization and, with `cascade=true` (default), every dataset it owns first. With `cascade=false` an organization that still owns datasets is refused with 409. Local catalog only. |

```bash
curl -s -X DELETE "$EP/resource/climate_research_2024" -H "Authorization: Bearer $TOKEN"
curl -s -X DELETE "$EP/organization/research_team?cascade=false" -H "Authorization: Bearer $TOKEN"
```

---

## S3 buckets and objects

Mounted only with `S3_ENABLED=True`; **every route requires the writer role**.
`503 S3 service is not configured` means the endpoint or keys are empty.
Setup: [minio-setup.md](minio-setup.md).

### Buckets

```bash
curl -s "$EP/s3/buckets/" -H "Authorization: Bearer $TOKEN"
# {"buckets": [{"name": "test-bucket", "creation_date": "…"}]}

curl -s -X POST "$EP/s3/buckets/" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "test-bucket", "region": "us-east-1"}'
# 201 {"message": "Bucket 'test-bucket' created successfully", "success": true}

curl -s "$EP/s3/buckets/test-bucket" -H "Authorization: Bearer $TOKEN"
curl -s -X DELETE "$EP/s3/buckets/test-bucket" -H "Authorization: Bearer $TOKEN"
```

`region` is optional. Creating an existing bucket is 409; deleting a bucket
that is not empty is 409; an unknown bucket is 404.

### Objects

```bash
# Upload (multipart); object_key defaults to the file name
curl -s -X POST "$EP/s3/objects/test-bucket" -H "Authorization: Bearer $TOKEN" \
  -F "file=@obs.csv" -F "object_key=2024/obs.csv"
# {"bucket": "test-bucket", "key": "2024/obs.csv", "size": 1234, "etag": "…"}

# List, optionally by prefix
curl -s "$EP/s3/objects/test-bucket?prefix=2024/" -H "Authorization: Bearer $TOKEN"

# Metadata
curl -s "$EP/s3/objects/test-bucket/2024/obs.csv/metadata" -H "Authorization: Bearer $TOKEN"

# Download
curl -s -o obs.csv "$EP/s3/objects/test-bucket/2024/obs.csv" -H "Authorization: Bearer $TOKEN"

# Presigned URLs (POST, body {expires_in}: seconds, 1–604800, default 3600)
curl -s -X POST "$EP/s3/objects/test-bucket/2024/obs.csv/presigned-download" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"expires_in": 3600}'
# {"url": "…", "expires_in": 3600}
curl -s -X POST "$EP/s3/objects/test-bucket/2024/new.csv/presigned-upload" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"expires_in": 600}'

# Delete
curl -s -X DELETE "$EP/s3/objects/test-bucket/2024/obs.csv" -H "Authorization: Bearer $TOKEN"
```

Upload and download pass the whole object through the API's memory. A
presigned URL points at `S3_ENDPOINT` as the API sees it (for the bundled
service, `minio:9000`), so it is usable only by clients that can resolve that
host.

---

## Pelican

Mounted only with `PELICAN_ENABLED=True`; every route requires the viewer
role, and `POST /pelican/import-metadata` the writer role.

| Route | Purpose |
|---|---|
| `GET /pelican/federations` | Known federations |
| `GET /pelican/browse?path=&federation=osdf&detail=false` | List a namespace |
| `GET /pelican/info?path=&federation=` | Object metadata |
| `GET /pelican/download?path=&federation=&stream=` | Download an object |
| `GET /pelican/read?path=&federation=` | Return an object inline; larger than `PELICAN_MAX_READ_BYTES` is 413 |
| `GET /pelican/subscribe` | Server-sent stream of file events from the event server |
| `GET /pelican/subscriptions` | Active subscriptions |
| `POST /pelican/import-metadata` | Add a Pelican object as a resource of a local dataset: `{pelican_url, package_id, resource_name?, resource_description?}` |

Event-server settings and credentials are described in
[configuration.md](configuration.md#pelican-federation-external-data-access).

---

## Access requests

Mounted always; every route answers 503 while `ENABLE_ACCESS_REQUESTS` is
false.

```bash
# Any signed-in user asks for access (one pending request per user; 409 otherwise)
curl -s -X POST "$EP/user/access-requests" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"justification": "I work on project X"}'

# Admin: list (default pending; status=pending|approved|rejected|all)
curl -s "$EP/user/access-requests?status=all" -H "Authorization: Bearer $TOKEN"

# Admin: approve with a tier (viewer | writer | admin; member = viewer)
curl -s -X POST "$EP/user/access-requests/<id>/approve" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"grant_type": "writer", "notes": "Welcome"}'

# Admin: reject
curl -s -X POST "$EP/user/access-requests/<id>/reject" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"notes": "Not part of the project"}'
```

Approval calls the identity provider with the approving admin's token; a
refusal there is passed through (401/403/404) and an unreachable provider is
502. Which group is granted is described in
[roles-and-permissions.md](roles-and-permissions.md#grant-an-existing-tier-to-a-user).

---

## Errors

Every error raised by the API has the same envelope
([`api/exceptions/handlers.py`](../api/exceptions/handlers.py)):

```json
{
  "error": "BadRequest",
  "detail": "Pre-CKAN is disabled and cannot be used.",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-10-08T12:00:00.000000+00:00",
  "path": "/dataset"
}
```

`correlation_id` is also returned in the `X-Correlation-ID` response header;
send your own `X-Correlation-ID` to have it used instead, and quote it when
reporting a problem — it is in the Endpoint's log lines for that request.
`detail` is usually a string, sometimes an object (the duplicate errors above)
or a list (validation errors).

Validation errors (pydantic v2) are 422 with one entry per problem:

```json
{
  "error": "ValidationError",
  "detail": [
    {"loc": ["body", "title"], "msg": "Field required", "type": "missing"},
    {"loc": ["body", "name"],
     "msg": "Value error, name must contain only lowercase letters, numbers, underscores, and hyphens",
     "type": "value_error"}
  ],
  "correlation_id": "…",
  "timestamp": "…",
  "path": "/dataset"
}
```

Status codes:

| Code | `error` | Typical cause |
|---|---|---|
| 200 / 201 | — | Success; creations answer 201. |
| 307 | — | Path without its trailing slash; follow the `Location`. |
| 400 | `BadRequest` | Catalog refused the operation, reserved extras key, `server` not enabled, keys/terms mismatch. |
| 401 | `Unauthorized` | Token invalid or expired (the identity provider rejected it). |
| 401 or 403 | `Unauthorized` / `Forbidden` | No `Authorization` header at all; answered by FastAPI's `HTTPBearer` with `Not authenticated` (the code depends on the FastAPI version installed; `requirements.txt` does not pin it). |
| 403 | `Forbidden` | Role tier too low, or outside the Endpoint's groups. |
| 404 | `NotFound` | Unknown dataset, resource, organization, bucket or object; or a route not mounted on this Endpoint (then the body is FastAPI's default `{"detail": "Not Found"}`). |
| 409 | `Conflict` | Duplicate Kafka dataset or service, organization still has datasets (`cascade=false`), bucket exists or is not empty, access request already pending or decided. |
| 413 | `HTTPError` | `/pelican/read` of an object larger than `PELICAN_MAX_READ_BYTES`. |
| 422 | `ValidationError` | Body, query or path does not match the model. |
| 500 | `InternalServerError` | Unhandled failure, or an S3 operation that failed outside S3's own error codes (for example an unreachable `S3_ENDPOINT`). |
| 502 | `BadGateway` | Identity provider unreachable or failing; staging catalog failure on publish; service proxy cannot reach its target. |
| 503 | `ServiceUnavailable` | Catalog unreachable during `GET /search`, S3 not configured, access requests disabled or no group configured for approval, `/ready` unhealthy. |
| 504 | `GatewayTimeout` | `GET /search` or the service proxy timed out. |
