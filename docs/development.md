# Development guide

For a developer taking over the NDP Endpoint API: where things are, how to run
it and its tests the way CI does, how a change and a release are made, and the
conventions the code follows. For running an Endpoint in production, see
[operations.md](operations.md); for every setting, see
[configuration.md](configuration.md).

## Repository layout

| Path | What it holds |
|---|---|
| `api/` | The FastAPI application. `api/main.py` builds the app and decides which routers are mounted. |
| `api/config/` | Settings classes, one per area (`swagger_settings.py`, `ckan_settings.py`, `catalog_settings.py`, `minio_settings.py`, `kafka_settings.py`, `affinities_settings.py`, `rexec_settings.py`, `otel_settings.py`). |
| `api/routes/` | Routers, one directory per area (register, search, update, delete, resource, status, user, health, minio, redirect), plus `pelican_routes.py`. |
| `api/services/` | The logic behind the routes, one directory per area, including `auth_services/` (token validation and authorization). |
| `api/repositories/` | The catalog repository interface and its CKAN and MongoDB implementations, the access-request store and the Pelican client. |
| `api/models/` | Pydantic request and response models. |
| `api/tasks/` | Background work: `metrics_task.py` (the periodic metrics report) and `leader.py` (leader election between workers). |
| `api/middleware/`, `api/exceptions/`, `api/telemetry/` | Correlation-id middleware, global exception handlers, OpenTelemetry setup. |
| `ui/` | The React web UI (react-scripts), built into the image and served at `/ui/`. |
| `install/` | The installer (`install.sh`), its Python helpers (`render_env.py`, `remembered_settings.py`) and its README. |
| `install/tests/` | Tests for the installer and its helpers, plus `sandbox.sh`, which runs the installer inside a throwaway Docker-in-Docker container. |
| `tests/` | Tests for the API. Files ending in `.py.disabled` are not collected. |
| `scripts/` | Release helpers used by CI: `check_release_version.py` and `extract_changelog.py`. |
| `docs/` | Documentation; [docs/README.md](README.md) is the index. |
| Repository root | `docker-compose.yml`, `Dockerfile.allinone`, `entrypoint.sh`, `example.env`, `requirements.txt`, `pytest.ini`, `pyproject.toml`, `test_all_endpoints.py`, `seed_sample_data.py`, `CHANGELOG.md`. |

## Running it locally

### Without Docker

CI and the image both use **Python 3.13** (`.github/workflows/*.yml`,
`FROM python:3.13-slim` in `Dockerfile.allinone`).

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp example.env .env        # then edit it, see below
uvicorn api.main:app --reload --port 8000
```

- Every settings class reads `.env` from the **current working directory**
  (`"env_file": ".env"`), and environment variables override it, so start
  uvicorn from the repository root.
- `example.env` is written for Docker Compose: hosts are service names
  (`mongodb`, `minio`, `kafka`, `jupyterlab`). When the API runs on the host,
  point them at what is reachable from it. With the bundled services started by
  Compose, MongoDB is published on `localhost:27018`, MinIO's API on
  `localhost:9002` and Kafka on `localhost:9094` (see `docker-compose.yml`).
- The settings that decide what the app mounts are `LOCAL_CATALOG_BACKEND` and
  `CKAN_LOCAL_ENABLED` (local catalog routes), `S3_ENABLED` (S3 routes) and
  `PELICAN_ENABLED` (Pelican routes). With `LOCAL_CATALOG_BACKEND=none` and
  `CKAN_LOCAL_ENABLED=False` nothing local is needed.
- `TEST_TOKEN` is accepted as a bearer token and resolves to a user with the
  `ndp_admin` role without contacting `AUTH_API_URL`
  (`api/services/auth_services/get_current_user.py`). If the variable is not
  set at all, the default is `testing_token`.
- The app writes a log file under `logs/` in the working directory.
- The interactive API docs are at `/docs`.

The UI is not served by uvicorn. In the image, nginx serves the built UI at
`${ROOT_PATH}/ui/` and `entrypoint.sh` writes `ui/build/config.js`, which
defines `window.__EP_CONFIG__` (`rootPath`, `affinitiesEpUuid` and the `OIDC_*`
values). The UI uses `rootPath` as the base URL of the API, so it expects the
API on the same origin. To work on the UI with the API, build the image.

### With Docker

```bash
cp example.env .env
docker compose up -d --build                       # the API and UI only
docker compose --profile mongodb up -d --build     # plus MongoDB
docker compose --profile full up -d --build        # every bundled service
```

The `api` service is built from `Dockerfile.allinone` (React build stage, then
Python 3.13 with nginx and supervisord running uvicorn with four workers) and
published on `${EP_API_PORT:-8002}`. The UI is then at
`http://localhost:8002/ui/`. The profiles are listed in
[operations.md](operations.md#what-runs).

`./install/install.sh` renders `.env` from `example.env` and starts the stack;
see [../install/README.md](../install/README.md). To test changes to the
installer without touching the host's Docker state, use
`./install/tests/sandbox.sh` (it copies the working tree, uncommitted changes
included).

## Running the tests as CI does

`.github/workflows/pr.yml` (pull requests to `main`) and
`.github/workflows/main.yml` (pushes to `main`) run the same two jobs.

Python job, on Python 3.13:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install black flake8

black --check --diff .
flake8 api/ tests/ scripts/ --max-line-length=88 --extend-ignore=E203,W503,E501,F401
pytest tests/ install/tests/ -v --cov=api --cov-report=xml --cov-report=term-missing
```

Coverage is uploaded to Codecov; an upload failure does not fail the job.

UI job, on Node 18 (the version of the `ui-builder` stage in
`Dockerfile.allinone`):

```bash
cd ui
npm ci
CI=true npm test -- --watchAll=false
```

`pytest.ini` sets `testpaths = tests install/tests`, `pythonpath = .` and
`asyncio_mode = strict`, so a bare `pytest` from the repository root runs both
suites.

### Test conventions

- `tests/` covers the API: routes, services, repositories
  (`tests/repositories/`), models, settings, middleware, the metrics task,
  leader election, the nginx configuration generated by `entrypoint.sh`, the
  Compose file and the release scripts. External systems (CKAN, MongoDB,
  MinIO, the authentication service, Affinities) are mocked.
- Authorization and routing are tested by sending HTTP requests through
  FastAPI's `TestClient` to an app with the router mounted, so dependency
  injection is exercised rather than the handlers being called directly
  (for example `tests/test_delete_routes_auth.py`,
  `tests/test_minio_routes_auth.py`).
- The installer tests in `install/tests/` run `install.sh` with `bash` and put
  stub executables (for example a `docker` that never answers) first on
  `PATH`; they are skipped where `bash` with `/dev/tcp` is not available.

### Against a running Endpoint

- `test_all_endpoints.py` exercises every route of a running Endpoint,
  creating test data and deleting it at the end. `EP_BASE_URL` selects the
  Endpoint (default `http://localhost:8002`) and `EP_TOKEN` the token (default
  `testing_token`). It reads `GET /status/` and skips, with the reason, the
  tests of features the Endpoint has switched off.

  ```bash
  EP_BASE_URL=http://localhost:8002 EP_TOKEN=<token> python test_all_endpoints.py
  ```

- `seed_sample_data.py` creates sample organizations, datasets, resources,
  services and S3 objects for demos. It targets `http://localhost:8002` with
  the token `testing_token`, both set at the top of the script.

## CI workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `pr.yml` | Pull request to `main` | black, flake8, pytest with coverage; UI tests. |
| `main.yml` | Push to `main`, manual | The same jobs as `pr.yml`. |
| `docker-publish.yml` | Tag `v*`, manual (with a version) | Publishes the image and the GitHub release, in this order: resolve the version from the tag (a version with a hyphen is a prerelease and never moves `latest`); `scripts/check_release_version.py <version>` fails the run if it differs from `swagger_version` in `api/config/swagger_settings.py`; `scripts/extract_changelog.py <version>` takes that version's section of `CHANGELOG.md` as release notes; build `Dockerfile.allinone` for `linux/amd64` and push `rbardaji/ndp-ep-api:<version>` and `rbardaji/ndp-ep-api:latest`; create the GitHub release last (or update it, if it exists). |
| `demo-deck.yml` | Push to `main` touching `docs/demo/**`, manual | Renders `docs/demo/NDP-demo-presentation.md` with Marp to HTML and PDF and publishes it to GitHub Pages. |

Because the release is created only after the image is pushed, a failed push
leaves no release; re-running the workflow finishes a partial run.

## Release procedure

1. Set `swagger_version` in `api/config/swagger_settings.py` to the new version
   (`X.Y.Z`).
2. Add a `## [X.Y.Z] - YYYY-MM-DD` section to `CHANGELOG.md`, below
   `## [Unreleased]`.
3. Open a pull request, wait for CI, merge.
4. Tag the merge commit `vX.Y.Z` and push the tag. `docker-publish.yml` does the
   rest.

## Change procedure

The procedure the maintainer follows for every change:

1. Open (or take) a GitHub issue describing the problem.
2. Branch from `main` as `fix/<issue>-<slug>` (or `feature/<issue>-<slug>`).
3. Fix it, with tests that fail before the fix and pass after.
4. Check it against a real running Endpoint, not only the unit tests.
5. Bump `swagger_version` and add the `CHANGELOG.md` section, referencing the
   issue (`(#NNN)`).
6. Open a pull request; wait for CI to be green; merge.
7. Tag the merge commit (see [Release procedure](#release-procedure)).

Commit messages follow the conventional style seen in the history:
`fix: ...`, `fix(install): ...`, `build: ...`, `docs: ...`.

## Code conventions

- **black** with line length 88 (`pyproject.toml`); CI runs
  `black --check --diff .` over the whole repository.
- **flake8** over `api/`, `tests/` and `scripts/` with
  `--max-line-length=88 --extend-ignore=E203,W503,E501,F401`.
- Docstrings use the NumPy style (`Parameters`, `Returns`, `Raises`).

## Where things live

- **Settings** — `pydantic-settings` classes in `api/config/`, each exposed as a
  module-level instance (`swagger_settings`, `ckan_settings`,
  `catalog_settings`, `s3_settings`, `kafka_settings`, ...). Field names map to
  upper-case environment variables; each class reads `.env`. `example.env` is
  the documented list of variables, and the installer renders `.env` from it.
- **Catalog repositories** — `api/repositories/base_repository.py` defines
  `DataCatalogRepository`; `ckan_repository.py` and `mongodb_repository.py`
  implement it. `catalog_settings.local_catalog` returns the implementation
  selected by `LOCAL_CATALOG_BACKEND`; `global_catalog` and `pre_catalog` are
  always CKAN. Adding a backend: [adding-catalog-backends.md](adding-catalog-backends.md).
- **Route mounting** — `api/main.py` mounts the local catalog routers only when
  `CKAN_LOCAL_ENABLED` is true and the backend is not `none`, the S3 routers
  only with `S3_ENABLED`, and the Pelican router only with `PELICAN_ENABLED`.
- **Authentication and authorization** — `api/services/auth_services/`:
  `get_current_user.py` validates the bearer token against `AUTH_API_URL`;
  `authorization_service.py` holds the role and group checks
  (`require_admin`, group-based access). Roles are described in
  [roles-and-permissions.md](roles-and-permissions.md).
- **Leader election** — the image runs four uvicorn workers, and each runs the
  FastAPI lifespan. `api/tasks/leader.py` makes one of them the leader by
  holding an exclusive `flock` on `ndp-ep-leader.lock` in the temporary
  directory; only the leader creates the `services` organization and runs the
  metrics task, and a waiting worker takes over if it stops.
- **Metrics** — `api/tasks/metrics_task.py` collects the metrics at startup
  and every `METRICS_INTERVAL_SECONDS`, logs them, and posts them to
  `METRICS_ENDPOINT` only when `IS_PUBLIC` is true. See
  [architecture/federation-and-metrics.md](architecture/federation-and-metrics.md).
- **Health** — `api/routes/health_routes/` (`/health` and `/ready`).
- **Runtime web server** — `entrypoint.sh` generates the nginx site from
  `ROOT_PATH` and the UI's `config.js` at every container start, then starts
  supervisord (nginx and uvicorn).
