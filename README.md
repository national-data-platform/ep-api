# National Data Platform - Endpoint API (NDP-EP API)

The NDP Endpoint is the service an institution runs to take part in the
[National Data Platform (NDP)](https://nationaldataplatform.org). It is a
FastAPI backend (`api/`) with a React web UI (`ui/`), shipped together as one
Docker image, plus an installer (`install/`) that registers an Endpoint with
the NDP Federation and brings it up.

An Endpoint:

- authenticates users against the NDP identity service (`AUTH_API_URL`) and
  enforces viewer / writer / admin roles;
- searches the NDP global catalog and, optionally, its own local catalog;
- optionally keeps a **local catalog** (MongoDB or CKAN) where datasets,
  organizations and resources (URLs, S3 objects, Kafka topics, services) are
  registered, and publishes datasets to the NDP staging catalog (Pre-CKAN);
- optionally manages S3 buckets and objects, Kafka streams, Pelican federation
  data and a JupyterLab link;
- reports metrics to the NDP Federation when it is listed there.

## Documentation

- [docs/README.md](docs/README.md) — index of all documentation
- [docs/architecture/overview.md](docs/architecture/overview.md) — how the
  pieces fit together
- [docs/configuration.md](docs/configuration.md) — every `.env` variable
- [docs/roles-and-permissions.md](docs/roles-and-permissions.md) — the
  viewer / writer / admin model
- [docs/architecture/federation-and-metrics.md](docs/architecture/federation-and-metrics.md)
  — registration with the Federation and the metrics contract
- [install/README.md](install/README.md) — the installer
- [ui/README.md](ui/README.md) — the web UI

## Catalogs

The API works with three catalogs. Global and staging are always CKAN; the
local one is chosen with `LOCAL_CATALOG_BACKEND`.

| Catalog | Setting | Access through this API |
|---|---|---|
| **Global** — the NDP central catalog | `CKAN_GLOBAL_URL` (default `https://nationaldataplatform.org/catalog`) | search (`server=global`, the default) |
| **Local** — this Endpoint's own catalog | `LOCAL_CATALOG_BACKEND=ckan \| mongodb \| none` | search (`server=local`), create, update, delete |
| **Staging** — Pre-CKAN | `PRE_CKAN_ENABLED`, `PRE_CKAN_URL`, `PRE_CKAN_API_KEY`, `PRE_CKAN_ORGANIZATION` | `POST /dataset/{dataset_id}/publish` copies a local dataset there |

The routes that write to the local catalog (registration, update, delete and
`/resource`, `/resources/search`) are mounted only when
`CKAN_LOCAL_ENABLED=True` **and** `LOCAL_CATALOG_BACKEND` is not `none`.
Despite its name, `CKAN_LOCAL_ENABLED` is the switch for any backend,
MongoDB included. See [docs/adding-catalog-backends.md](docs/adding-catalog-backends.md)
for adding another backend.

## Quick start

### With the installer

The installer registers the Endpoint with the Federation (or uses an existing
configuration id), writes `.env`, and starts the stack with Docker Compose:

```bash
bash <(curl -fsSL https://bit.ly/ndp-ep)
```

or, from a checkout:

```bash
./install/install.sh --help
```

See [install/README.md](install/README.md) and
[docs/installing-with-the-script.md](docs/installing-with-the-script.md).

### With Docker

Requirements: Docker, and Docker Compose for the bundled services.

The published image is `rbardaji/ndp-ep-api`, built from
[Dockerfile.allinone](Dockerfile.allinone). Inside the container nginx listens
on port **80** and serves:

- the UI at `${ROOT_PATH}/ui/`
- the API at `${ROOT_PATH}/`, and also at `${ROOT_PATH}/api/`

uvicorn (4 workers) listens only on `127.0.0.1:8000` inside the container.

1. Create the configuration:

   ```bash
   cp example.env .env
   ```

   `example.env` documents every variable; [docs/configuration.md](docs/configuration.md)
   is the full reference. `example.env` is written as a demo with the optional
   integrations switched on and pointing at the bundled services
   (`KAFKA_CONNECTION`, `USE_JUPYTERLAB`, `S3_ENABLED`, `PELICAN_ENABLED` are
   `True`, `LOCAL_CATALOG_BACKEND=mongodb`). Switch off what you do not run.
   It also sets `IS_PUBLIC=True`, which posts metrics to the Federation —
   set it to `False` for an Endpoint that is not registered there.

2. Run the published image:

   ```bash
   docker run -p 8002:80 --env-file .env rbardaji/ndp-ep-api
   ```

   or build from this checkout and start it with Compose, which publishes
   host port `${EP_API_PORT:-8002}` to container port 80:

   ```bash
   docker compose up -d --build
   ```

3. Check it:

   - UI: http://localhost:8002/ui/
   - API documentation (Swagger): http://localhost:8002/docs
   - Liveness: http://localhost:8002/health
   - Readiness: http://localhost:8002/ready (HTTP 503 if an enabled
     dependency is down)

   `/status/` needs a token and answers 401 without one.

`TEST_TOKEN` (default `testing_token`) is accepted as a Bearer token with the
`ndp_admin` role, without contacting the identity service. It is meant for
development only: **set `TEST_TOKEN=` (empty) in production.**

### Compose profiles

`docker-compose.yml` always starts the `api` service. Optional services are
enabled with `--profile <name>`:

| Profile | Services | Host ports |
|---|---|---|
| `mongodb` | MongoDB 7 (user `admin`, password `admin123`) | 27018 |
| `mongo-express` | Mongo Express, a web console for that MongoDB; use with `mongodb` | 8082 |
| `s3` | `pgsty/silo:RELEASE.2026-09-16T00-00-00Z`, a MinIO fork (MinIO images are no longer published); user `minioadmin`, password `minioadmin123` | 9002 (S3 API), 9003 (console) |
| `kafka` | Zookeeper, Kafka, Kafka UI | 9094 → 9092, 9095 → 9093 (Kafka); 8081 (Kafka UI) |
| `jupyter` | JupyterLab (`jupyter/scipy-notebook`, token `testing_token`) | 8888 |
| `pelican` | Pelican registry, director, origin, cache | 8444, 8445, 8446-8447, 8448-8449 |
| `full` | all of the above | |

Inside the Compose network the services are reached by name: `mongodb:27017`,
`minio:9000`, `kafka:9093`, `jupyterlab:8888`. The credentials above are fixed
demo values in `docker-compose.yml`.

```bash
docker compose --profile mongodb --profile s3 up -d --build
```

The Pelican services need TLS and federation setup that this repository does
not provide; on a fresh machine they restart in a loop. `full` includes them.
Start only the profiles you need.

`docker compose up` reuses an image it has already built. After pulling new
code, rebuild (`docker compose up -d --build`, or
`docker compose build --no-cache api`). The running version is shown at
`/docs`.

### Common configurations

**No local catalog.** Search the global catalog only; nothing is stored
locally:

```bash
LOCAL_CATALOG_BACKEND=none
CKAN_LOCAL_ENABLED=False
PRE_CKAN_ENABLED=False
KAFKA_CONNECTION=False
S3_ENABLED=False
PELICAN_ENABLED=False
USE_JUPYTERLAB=False
```

**MongoDB catalog from the `mongodb` profile:**

```bash
LOCAL_CATALOG_BACKEND=mongodb
CKAN_LOCAL_ENABLED=True
MONGODB_CONNECTION_STRING=mongodb://admin:admin123@mongodb:27017
MONGODB_DATABASE=ndp_local_catalog
```

```bash
docker compose --profile mongodb up -d --build
```

The connection string must carry the credentials; the bundled MongoDB is
started with them. `mongodb` is the service name, reachable from the `api`
container only.

**An existing CKAN:**

```bash
LOCAL_CATALOG_BACKEND=ckan
CKAN_LOCAL_ENABLED=True
CKAN_URL=https://your-ckan.example.org/
CKAN_API_KEY=<a CKAN API token>
CKAN_VERIFY_SSL=True        # False for a self-signed certificate
```

**Publishing to the staging catalog:**

```bash
PRE_CKAN_ENABLED=True
PRE_CKAN_URL=<provided by NDP>
PRE_CKAN_API_KEY=<provided by NDP>
PRE_CKAN_ORGANIZATION=<the organization that key may write to>
```

### Deploying on an IP address without TLS

- Use `http://<host>:<port>`; a bare IP address has no certificate for
  `https://`. Use the host's real IP or `localhost`, not a container or pod
  address.
- Identity-provider sign-in (`OIDC_ENABLED`) needs https; on plain http the
  UI shows the button disabled. `localhost` counts as secure.
- `GET /status/kafka-details` returns `KAFKA_HOST` and `KAFKA_PORT` exactly as
  configured, and streaming clients connect to that address. A client outside
  the Docker network cannot resolve the internal name `kafka:9093`.

### Logs

Inside the container, uvicorn writes to `/var/log/uvicorn.out.log` and
`/var/log/uvicorn.err.log`, nginx to `/var/log/nginx/`, and the metrics task
also to `/app/logs/metrics_<start time>.log`. `docker logs` shows the
supervisor output only.

## Access control

On every route that needs one, the Bearer token is validated by posting it to
`AUTH_API_URL`, which returns the user's `roles` and `groups`. `TEST_TOKEN` is
the exception (see above).

### Role tiers

| Tier | Accepted roles |
|---|---|
| admin | `ndp_admin`, `group:<g>:admin`, legacy `<AFFINITIES_EP_UUID>_admin` |
| writer | the admin roles, `ndp_writer`, `ndp_editor`, `group:<g>:writer`, `group:<g>:editor` |
| viewer | the writer roles, `ndp_viewer`, `group:<g>:viewer` |

`<g>` is any entry of `GROUP_NAMES` or `AFFINITIES_EP_UUID`. Comparison is
case-insensitive. The full model, and how roles are granted, is in
[docs/roles-and-permissions.md](docs/roles-and-permissions.md).

### Group-based access (`ENABLE_GROUP_BASED_ACCESS`)

With `ENABLE_GROUP_BASED_ACCESS=True`, a user must **also** pass the endpoint
access gate: belong to a group listed in `GROUP_NAMES` (comma-separated,
case-insensitive, leading `/` ignored), or belong to the group named
`AFFINITIES_EP_UUID`, or hold `ndp_admin`. An empty `GROUP_NAMES` leaves only
the last two. The gate applies to writer- and viewer-tier routes and to
`GET /user/info`, which the UI calls at login, so a user who fails it cannot
enter the UI.

The installer sets `ENABLE_GROUP_BASED_ACCESS=True` and `GROUP_NAMES` to the
group the Federation created for the Endpoint.

### What each route requires

| Routes | Requirement |
|---|---|
| `GET`/`POST /search`, `GET /organization`, `GET /resource/{id}`, `GET /resources/search`, `/services/redirect/...`, `/health`, `/ready`, `POST /user/login`, `POST /token`, `/docs` | none |
| `/status/`, `/status/metrics`, `/status/jupyter`, `/status/kafka-details`, `POST /user/access-requests` | any valid token |
| `GET /user/info` | valid token, plus the group gate when enabled |
| `GET /pelican/*` | viewer |
| every other `POST`, `PUT`, `PATCH`, `DELETE`; all `/s3/*` routes, including `GET`; `GET /status/rexec`; `POST /pelican/import-metadata` | writer |
| `GET /user/access-requests`, `POST /user/access-requests/{id}/approve` and `/reject` | admin |

The writer requirement applies whether or not `ENABLE_GROUP_BASED_ACCESS` is
on; a user with a valid token but no writer-tier role gets 403.

### Access requests

With `ENABLE_ACCESS_REQUESTS=True`, a user without access can request it from
the login screen, and an admin approves or rejects it from the UI. Requests are
stored in MongoDB through `MONGODB_CONNECTION_STRING` (collection
`ACCESS_REQUESTS_COLLECTION`), whatever the catalog backend. Approval adds the
user to the first `GROUP_NAMES` entry, falling back to `AFFINITIES_EP_UUID`,
and for writer or admin also assigns that role on the group, through the
identity provider with the approving admin's token. With the setting off,
these routes answer 503.

## Metrics

When `IS_PUBLIC=True`, the Endpoint posts a metrics report to
`METRICS_ENDPOINT` at startup and then every `METRICS_INTERVAL_SECONDS`
(default 3300). Only one uvicorn worker sends it. A failed post is logged and
not retried. With `IS_PUBLIC=False` the report is only logged. The payload
and behaviour are specified in
[docs/architecture/federation-and-metrics.md](docs/architecture/federation-and-metrics.md#2-metrics).

## MCP

The API is also exposed as a Model Context Protocol server (via
`fastapi-mcp`) at `/mcp` on the published port, e.g.
`http://localhost:8002/mcp` (`${ROOT_PATH}/mcp` when `ROOT_PATH` is set). Its
tools are the API's operations, with the same authentication.

## Pelican

With `PELICAN_ENABLED=true` the API mounts `/pelican/*` for reading from
[Pelican](https://pelicanplatform.org) federations such as OSDF. Every route
needs a Bearer token with the viewer tier; `POST /pelican/import-metadata`
needs writer.

| Route | Purpose |
|---|---|
| `GET /pelican/federations` | known federations (`osdf`, `path-cc`) |
| `GET /pelican/browse?path=...&federation=osdf&detail=false` | list a namespace |
| `GET /pelican/info?path=...` | object metadata |
| `GET /pelican/download?path=...&stream=true` | download an object |
| `GET /pelican/read?path=...` | return an object's contents inline, up to `PELICAN_MAX_READ_BYTES` (default 10 MiB; larger answers 413) |
| `GET /pelican/subscribe?event_source=...` | Server-Sent Events for file events in a namespace, from the Pelican event server (`PELICAN_EVENT_*`) |
| `GET /pelican/subscriptions` | the event-server subscriptions this Endpoint holds |
| `POST /pelican/import-metadata` | add a `pelican://` object as a resource of a local dataset |

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8002/pelican/browse?path=/ospool/uc-shared/public&detail=true"
```

`PELICAN_FEDERATION_URL`, when set, is used for every request instead of the
`federation` parameter. `PELICAN_DIRECT_READS=True` reads from origins rather
than through caches.

The `pelican` Compose profile starts a local registry, director, origin and
cache. The origin mounts the MinIO data volume read-only and exports it under
the federation prefix `/ndp-demo`, as configured in
[pelican-origin-config.yaml](pelican-origin-config.yaml). See the warning
under [Compose profiles](#compose-profiles).

## Development

```bash
pip install -r requirements.txt black flake8
pytest                      # tests/ and install/tests/
black --check . && flake8 api/ tests/ scripts/ --max-line-length=88 --extend-ignore=E203,W503,E501,F401
cd ui && npm ci && npm test -- --watchAll=false
```

These are the checks the `pr.yml` and `main.yml` workflows run.
`test_all_endpoints.py` exercises the routes of a running Endpoint
(`EP_BASE_URL`, `EP_TOKEN`).

## Releasing

The GitHub release and the Docker Hub image are both produced by the **Publish
Docker image** workflow (`.github/workflows/docker-publish.yml`), which runs
when a `v*` tag is pushed. The release is created as the workflow's last step,
once the image is on Docker Hub, so a failed build never leaves a release
pointing at an image that does not exist.

1. Bump `swagger_version` in `api/config/swagger_settings.py` and move the
   `## [Unreleased]` notes into a new `## [X.Y.Z]` section of
   [CHANGELOG.md](CHANGELOG.md).
2. Commit that to `main`.
3. Tag and push:
   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```

The workflow then validates the tag, builds
[Dockerfile.allinone](Dockerfile.allinone) for `linux/amd64`, pushes
`rbardaji/ndp-ep-api:X.Y.Z` (plus `latest`), and finally creates the GitHub
release with the notes taken from that version's CHANGELOG section.

Do not create the GitHub release by hand — the workflow does it.

**Prereleases.** A tag with a SemVer prerelease identifier (`v0.35.0-rc1`) is
detected automatically: the image is pushed under its own tag only, `latest` is
left alone, and the GitHub release is marked as a prerelease.

**If a run fails**, no release is created. Fix the cause and run the workflow
again from the Actions tab with the same version — it will finish the release
without needing a new tag.

**Checks that run before anything is published:**

- The tag must match `swagger_version`, which the API reports in `/docs` and
  in its metrics.
- The version must have a non-empty `CHANGELOG.md` section to use as notes.

Both can be run locally:

```bash
python scripts/check_release_version.py v0.34.18
python scripts/extract_changelog.py v0.34.18
```

**Required repository secrets:** `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`
(a Docker Hub access token with Read & Write permissions).

## License

MIT — see [LICENSE](LICENSE).
