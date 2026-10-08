# Operations guide

For whoever runs an NDP Endpoint: what is running, where its state is, how to
upgrade, back up and diagnose it, and what to check before exposing it in
production. For every setting, see [configuration.md](configuration.md); for
working on the code, see [development.md](development.md).

## Installing

- [installing-with-the-script.md](installing-with-the-script.md) — the
  installer, step by step.
- [../install/README.md](../install/README.md) — every installer flag,
  registration with the Federation, and how the installer works.

The installer renders `.env` from `example.env`, then runs
`docker compose --profile <...> up -d --build` from the repository checkout and
waits for `${ROOT_PATH}/health` to answer 200.

## What runs

Everything is defined in `docker-compose.yml`. The `api` service always starts;
the others start only with their Compose profile.

| Container | Service | Profiles | Host port → container port |
|---|---|---|---|
| `ndp-ep-api` | API and UI (nginx + uvicorn) | always | `${EP_API_PORT:-8002}` → 80 |
| `ndp-mongodb` | MongoDB 7 | `mongodb`, `full` | 27018 → 27017 |
| `ndp-minio` | S3-compatible storage (`pgsty/silo`, a MinIO fork) | `s3`, `full` | 9002 → 9000 (API), 9003 → 9001 (console) |
| `ndp-zookeeper` | ZooKeeper for Kafka | `kafka`, `full` | none |
| `ndp-kafka` | Kafka | `kafka`, `full` | 9094 → 9092, 9095 → 9093 |
| `ndp-kafka-ui` | Kafka web UI | `kafka`, `full` | 8081 → 8080 |
| `ndp-mongo-express` | MongoDB web console | `mongo-express`, `full` | 8082 → 8081 |
| `ndp-jupyterlab` | JupyterLab | `jupyter`, `full` | 8888 → 8888 |
| `ndp-pelican-registry` | Pelican registry | `pelican`, `full` | 8444 → 8444 |
| `ndp-pelican-director` | Pelican director | `pelican`, `full` | 8445 → 8444 |
| `ndp-pelican-origin` | Pelican origin | `pelican`, `full` | 8446 → 8443, 8447 → 8444 |
| `ndp-pelican-cache` | Pelican cache | `pelican`, `full` | 8448 → 8443, 8449 → 8444 |

The installer only ever adds the `mongodb` profile (MongoDB catalog installed
by it, or access requests without a MongoDB of their own), `s3` (S3 without
`--s3-endpoint`) and `kafka` (when the Federation registration enables
streaming). It never starts `mongo-express`.

Inside `ndp-ep-api`, supervisord runs nginx on port 80 and uvicorn on
`127.0.0.1:8000` with four workers. nginx serves the UI at `${ROOT_PATH}/ui/`
and proxies `${ROOT_PATH}/` (and the alias `${ROOT_PATH}/api/`) to uvicorn.

When the installer installs CKAN (`--backend ckan` without `--ckan-url`), CKAN
is a separate project (`sci-ndp/pop-ckan-docker`) cloned to `../ndp-ckan` next
to this checkout (or `--ckan-dir`), with its own `.env` and its own Compose
stack, started with `docker compose up -d --build` in that directory. Its
default host ports are 8443 (https), 81 (http) and 5000 (application).

## Where state lives

| What | Where |
|---|---|
| Endpoint configuration | `.env` in the repository root. Git-ignored. Every re-run of the installer saves the previous one as `.env.backup.<timestamp>` (mode 600) before overwriting it. |
| Installer state | `.env.install-state` in the repository root, mode 600. Holds the CKAN API key, CKAN URL, sysadmin name and password the installer created, so a re-run reuses them instead of minting another token. |
| MongoDB data | Docker volumes `mongodb_data` and `mongodb_config`. |
| S3 objects | Docker volume `minio_data` (also mounted read-only into the Pelican origin). |
| Kafka | Docker volumes `kafka_data`, `zookeeper_data`, `zookeeper_log`. |
| JupyterLab | Docker volume `jupyterlab_data`. |
| Pelican | Docker volumes `pelican_registry_data`, `pelican_director_data`, `pelican_origin_data`, `pelican_cache_data`. |
| CKAN (when installed by the installer) | `../ndp-ckan`: its `.env` and the volumes of its own Compose project. |

Compose prefixes volume names with the project name, which defaults to the
directory name of the checkout: `docker volume ls` shows, for example,
`ep-api_mongodb_data`.

The `ndp-ep-api` container itself keeps no state that is not regenerated:
`entrypoint.sh` rewrites the nginx configuration and the UI's `config.js` at
every start.

## Upgrading

The `api` service is **built locally** from the checkout (`build:` in
`docker-compose.yml`), so `docker compose pull` does not upgrade it. Upgrading
means moving the checkout to the new version and rebuilding.

**With the installer.** Run it again; it renders `.env` again and runs
`up -d --build`, which rebuilds the image from the checkout.

- Run from the web (`bash <(curl -fsSL ...)`), it fetches `EP_REPO_REF`
  (default `main`; a tag such as `v0.34.45` pins a version) into
  `EP_INSTALL_DIR` (default `~/ndp-ep`) and runs from there.
- Run from an existing checkout, it uses that checkout as it is: update it
  first (`git fetch --tags && git checkout vX.Y.Z`).
- It refuses a host port that is already in use, including by the running
  `ndp-ep-api`, so stop the API first: `docker compose stop api`.
- `.env` is rendered again from `example.env` plus the installer's answers;
  edits made by hand to `.env` are in the `.env.backup.<timestamp>` it saves.

**Without the installer.** From the checkout:

```bash
git fetch --tags && git checkout vX.Y.Z
EP_API_PORT=<port> docker compose --profile <profile> ... up -d --build
```

`EP_API_PORT` is not stored in `.env`; without it the API is published on
8002. Pass the same profiles the installation uses, or their containers are
left as they are.

The image is also published on Docker Hub as `rbardaji/ndp-ep-api:<version>`
and `:latest` for deployments that do not build from the repository.

## Backup and restore

Back up `.env` and `.env.install-state` (both hold credentials and exist
nowhere else) and the Docker volumes in use.

MongoDB, with the bundled container and its default credentials:

```bash
docker exec ndp-mongodb mongodump --username admin --password admin123 \
  --authenticationDatabase admin --archive > mongodb.archive

docker exec -i ndp-mongodb mongorestore --username admin --password admin123 \
  --authenticationDatabase admin --archive < mongodb.archive
```

Any volume, as a tar archive (stop the container that uses it first, so the
copy is consistent):

```bash
docker compose stop minio
docker run --rm -v ep-api_minio_data:/data -v "$PWD":/backup alpine \
  tar czf /backup/minio_data.tgz -C /data .
docker compose start minio
```

Restore by extracting the archive into the volume with the container stopped
(`tar xzf /backup/minio_data.tgz -C /data`). Use the volume name `docker volume
ls` shows for your project.

CKAN installed by the installer keeps its data in the volumes of its own
Compose project in `../ndp-ckan`; back those up the same way.

## Logs

- `docker logs ndp-ep-api` — the container's entrypoint and supervisord
  output.
- Inside the container (`docker exec -it ndp-ep-api sh`):
  - `/var/log/uvicorn.err.log` and `/var/log/uvicorn.out.log` — the API. The
    application logs to the console handler, which writes to stderr, so most
    API messages are in `uvicorn.err.log`.
  - `/var/log/nginx/access.log` and `/var/log/nginx/error.log` — nginx.
  - `/var/log/supervisor/supervisord.log` — supervisord.
  - `/app/logs/metrics_<timestamp>.log` — the application log, including each
    metrics payload, rotated at 5 MB with three backups.
- `docker compose logs <service>` for the other containers.

## Health

Both routes need no token and are served under `${ROOT_PATH}`.

- **`GET /health`** — liveness. Answers 200 with `"status": "healthy"` while
  the API process runs; it checks no dependency. The container healthcheck
  calls it on uvicorn directly (`http://localhost:8000/health`) every 30
  seconds.
- **`GET /ready`** — readiness. Checks each configured dependency and reports
  `up`, `down` or `disabled` for each, with latency:
  - `local_catalog` — the CKAN or MongoDB local catalog; `disabled` when the
    backend is `none` or `CKAN_LOCAL_ENABLED` is false.
  - `pre_ckan` — the staging catalog, when `PRE_CKAN_ENABLED` and its URL and
    key are set; also reports `organization_configured`.
  - `minio` — S3 storage, when enabled and configured.
  - `kafka` — Kafka, when `KAFKA_CONNECTION` is true.
  - `affinities` — Affinities and whether it knows `AFFINITIES_EP_UUID`. Reported
    only: it does not affect the verdict.

  It answers 200 when every check other than `affinities` is `up` or
  `disabled`, and 503 otherwise. It does not check the global catalog or the
  authentication service.

`GET /status/` reports the version and which features are switched on
(`kafka_enabled`, `s3_enabled`, `jupyterlab_enabled`, `pre_ckan_enabled`,
`access_requests_enabled`, the local catalog backend and whether it is
connected).

## Common problems

**The installer stops with "Port N is already in use".** The installer checks
the API port before starting and names the container holding it, if any.
Choose another with `--ep-api-port <port>`, or stop what is using it (for an
upgrade, `docker compose stop api`). CKAN's ports are checked the same way;
change them with `--ckan-ssl-port`, `--ckan-http-port` and `--ckan-app-port`.

**`/search` answers 503 "Global catalog is not reachable" or "Global catalog
is currently unavailable".** The Endpoint could not reach the global CKAN
catalog at `CKAN_GLOBAL_URL` (default `https://nationaldataplatform.org/catalog`).
Check outbound network access from the host. The same 503 with "Local" names
the local CKAN catalog.

**Routes are missing from `/docs`, or answer 404.** Routers are mounted only
for features that are switched on (`api/main.py`):

- S3 bucket and object routes — `S3_ENABLED=True`.
- Registration, update, delete and resource routes (datasets, URL, S3 and
  Kafka resources, services, organizations) — `CKAN_LOCAL_ENABLED=True` and
  `LOCAL_CATALOG_BACKEND` other than `none`.
- Pelican routes — `PELICAN_ENABLED=True`.

The UI hides its S3, streaming and catalog entries according to `GET /status/`.
Settings are read when the container is created: after changing `.env`,
recreate it with `EP_API_PORT=<port> docker compose up -d --force-recreate api`
(`docker compose restart` keeps the old environment).

**401, 403 or 502 on authenticated routes.** Tokens are validated against
`AUTH_API_URL` (`api/services/auth_services/get_current_user.py`):

- 401 — the authentication service rejected the token (invalid or expired).
- 502 — the authentication service could not be reached or answered with an
  error. Check `AUTH_API_URL` and outbound access from the host.
- 403 on a write — the user is not allowed to write on this Endpoint. With
  `ENABLE_GROUP_BASED_ACCESS=True` the user must hold `ndp_admin`, belong to
  the group named by `AFFINITIES_EP_UUID`, or belong to one of `GROUP_NAMES`;
  in every case a write also needs the writer tier or above. Admin-only routes
  need the admin tier (`ndp_admin`, `group:<AFFINITIES_EP_UUID>:admin` or
  `<AFFINITIES_EP_UUID>_admin`). The application log records what was
  required. See [roles-and-permissions.md](roles-and-permissions.md).

**Access requests answer 503.** "Access-request workflow is disabled on this
deployment" means `ENABLE_ACCESS_REQUESTS` is not true. Requests are stored in
MongoDB through `MONGODB_CONNECTION_STRING`, so that MongoDB must be reachable
whatever the catalog backend is. Approving a request answers 503 "Endpoint UUID
is not configured" when `AFFINITIES_EP_UUID` is empty: the user is added to the
group named by that UUID.

**Metrics do not reach the Federation.** The report is posted only when
`IS_PUBLIC=True`; with `False` it is collected and logged and nothing leaves
the Endpoint. The installer sets `IS_PUBLIC=False` unless a Federation
registration says the Endpoint is public. The report goes to `METRICS_ENDPOINT`
(the installer writes `<federation-url>/metrics/`) at startup and every
`METRICS_INTERVAL_SECONDS` (default 3300). Look for "Successfully posted
metrics" or "Error posting metrics" in the logs.

## Security checklist for production

- **`TEST_TOKEN`.** Any request carrying it as a bearer token is accepted as a
  user with the `ndp_admin` role, without contacting the authentication
  service. `example.env` sets `TEST_TOKEN=testing_token` and the installer does
  not change it, and if the variable is absent the default is also
  `testing_token`. Set it explicitly to empty (`TEST_TOKEN=`) in `.env`.
- **Bundled default credentials** in `docker-compose.yml` are the same in
  every deployment: MongoDB `admin` / `admin123`; mongo-express `admin` /
  `admin123`; MinIO `minioadmin` / `minioadmin123` (also the defaults of
  `S3_ACCESS_KEY` / `S3_SECRET_KEY`); JupyterLab token `testing_token`. Change
  them before exposing those services, and update the matching settings in
  `.env` (`MONGODB_CONNECTION_STRING`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`).
- **CORS** is fully open: `api/main.py` allows every origin, method and header,
  with credentials.
- **Published ports.** `docker-compose.yml` publishes MongoDB (27018), MinIO
  (9002, 9003), Kafka (9094, 9095), Kafka UI (8081), mongo-express (8082),
  JupyterLab (8888) and the Pelican services without a bind address, that is on
  every host interface. Do not expose the MongoDB and MinIO ports, or the
  admin consoles, to the public network.
- **TLS.** The container serves plain HTTP on port 80; TLS is terminated by
  whatever is in front of it. Identity-provider sign-in in the UI needs https
  (see `OIDC_*` in [configuration.md](configuration.md)).
- **Certificate verification.** Keep `CKAN_VERIFY_SSL` and
  `PRE_CKAN_VERIFY_SSL` true except for a CKAN with a self-signed certificate
  (the installer sets `CKAN_VERIFY_SSL=False` for the CKAN it installs).
- **Secrets on disk.** `.env`, `.env.backup.*` and `.env.install-state` hold
  credentials; the installer creates the backups and the state file with mode
  600.
