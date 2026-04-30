# Changelog

All notable changes to the NDP-EP API project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.19.2] - 2026-04-30

### Added
- Dataset Management page: a new "Organization" select on the right side of the datasets card header now filters the visible rows by the organization that owns them. The filter runs client-side on the data the page already fetches, so no extra API call is needed:
  - Default value is "All organizations", which keeps the current behavior of showing every dataset
  - When a filter is active, the dataset count next to the title becomes "Datasets (X of Y)" so the user knows how many were hidden
  - When the filter matches no rows, the empty-state copy suggests trying a different organization or going back to the full list, instead of nudging the user to create a new dataset
  - The select reuses the organization name strings the page already fetches for the create/edit form, so the dropdown values match the strings rendered in the table's "Organization" column

## [0.19.1] - 2026-04-30

### Fixed
- Top header: when an admin session showed the "Access Requests" link, the row no longer fit horizontally — "Access Requests" wrapped onto a second line and the Logout button on the right ended up looking misaligned. The header now stays on a single row regardless of which nav items are visible:
  - Every nav link/button label uses `white-space: nowrap` so labels never wrap mid-word
  - Nav and right-cluster gaps tightened from 1.5rem to 1rem; link padding from 0.75rem 1rem to 0.5rem 0.75rem; Logout button padding from 0.75rem 1.5rem to 0.5rem 1rem
  - Inner container max width raised from 1200px to 1400px so the header has more horizontal room before falling back on the tighter sizes

## [0.19.0] - 2026-04-30

### Added
- Dataset Management page: each row whose `extras.status` is not "submitted" now exposes a primary "Publish" action button before the Edit/Delete buttons, so a user can push a local dataset to PRE-CKAN directly from the table without leaving the page (no more Swagger or curl round-trip):
  - The button calls `POST /dataset/{dataset_id}/publish` through a new `generalDatasetAPI.publish` client method
  - Per-row publishing state disables the button and switches its label to "Publishing…" while the request is in flight, so double-clicks cannot fire the publish twice
  - On success the datasets list is refetched and the status icon flips from Home to Clock automatically
  - When the backend had to auto-rename the dataset (because its `name` was already in use in PRE-CKAN), the response's `warning` field is surfaced via the yellow warning banner instead of the green success banner, so the user notices that the published name/title differ from theirs
  - Once a dataset is already submitted the button is hidden, preventing a re-publish that would just create a renamed duplicate

## [0.18.2] - 2026-04-30

### Added
- Dataset Management page: a new "Status" column on the datasets table surfaces each dataset's submission state at a glance, using a small icon instead of the raw status string so the table stays compact:
  - Amber Clock when the dataset has been published to PRE-CKAN (`extras.status === "submitted"`) and is awaiting review
  - Gray Home when the dataset has no status entry (local-only, never published)
  - Gray AlertCircle for any unrecognized status, with the raw value still exposed via the hover tooltip so the row never silently hides state
- Each icon is wrapped in a `title`-bearing span so hovering reveals the underlying status text without cluttering the table

## [0.18.1] - 2026-04-30

### Removed
- Repository root: orphaned `package.json` and `package-lock.json` (legacy `pop-api-frontend` v1.3.0-alpha.2). The actual frontend lives under `ui/` (`ndp-ep-frontend`) and is the only one consumed by the Docker build, so the root-level files were unused and only added confusion about which is the real frontend

## [0.18.0] - 2026-04-29

### Changed
- `POST /dataset/{dataset_id}/publish` no longer fails when the dataset's `name` is already in use in PRE-CKAN. The publish is retried automatically with a timestamp suffix on both `name` and `title`, mirroring the auto-rename behavior of `POST /dataset`:
  - `name` becomes `<original>-<YYYYMMDDHHMMSS>` so it still satisfies CKAN's slug constraint (`^[a-z0-9_-]+$`)
  - `title` becomes `<original> (YYYY-MM-DD HH:MM:SS)` so the rename is obvious to humans
  - The response keeps a `201 Created` status and now also returns the final `name`, `title` and a `warning` field describing the rename (or `null` when no rename happened)
  - The local dataset's `status=submitted` mirror is still applied after the (possibly renamed) publish succeeds, so the originating Endpoint can still tell which datasets are pending review
- Other publish failures (PRE-CKAN disabled, dataset not found locally, organization missing in PRE-CKAN, transport errors) keep their existing semantics and do not trigger the auto-rename retry

## [0.17.3] - 2026-04-29

### Changed
- UI footer: the displayed version is now read at runtime from the backend's OpenAPI document (`info.version` exposed at `/openapi.json`), so it always matches the deployed API and no longer needs a manual bump on every release. While the version is being fetched, or if the request fails, the footer renders a neutral placeholder

### Removed
- UI footer: the "© <year> National Data Platform. All rights reserved." line has been removed; the version row now only shows the "NDP EndPoint" label and the live version badge

## [0.17.2] - 2026-04-29

### Removed
- Dataset Management page: the "Type" column on the datasets table has been removed. The page already filters out URL / S3 / Kafka / Service datasets, so by construction every row was labeled "General" and the column carried no useful signal

## [0.17.1] - 2026-04-29

### Removed
- Dataset Management, Kafka Topics, URL Resources and S3 Resources pages: the "Controls" card that wrapped the create / refresh buttons (and showed a static "📍 Local Server Only" badge) has been removed. The page header now flows directly into the action buttons, which removes visual weight that was not carrying any function

## [0.17.0] - 2026-04-29

### Changed
- `POST /dataset` no longer rejects requests whose `name` (or its derived URL) is already in use. Instead, the dataset is created with an automatic timestamp suffix and the response keeps a `201 Created` status while including a `warning` field that explains the rename:
  - `name` becomes `<original>-<YYYYMMDDHHMMSS>` so it still satisfies CKAN's slug constraint (`^[a-z0-9_-]+$`)
  - `title` becomes `<original> (YYYY-MM-DD HH:MM:SS)` so the rename is obvious to humans
  - The response body now also returns the final `name` and `title` so any consumer (UI, CURL, scripts) can detect and surface the rename
- The previous `409 Conflict` response with a structured `detail` object has been removed from this endpoint, since the duplicate-name case is now handled transparently
- Dataset Management page: when the backend renames a duplicate dataset, the create form now shows a dedicated yellow warning banner prefixed with "WARNING:" instead of the green success banner, so the user immediately notices that the stored `name` and `title` differ from the ones they submitted

### Fixed
- Dataset Management page: creating a dataset that triggered a backend error with a structured `detail` payload used to display the meaningless string "Failed to create dataset: [object Object]". A new helper now flattens structured detail objects into a readable message before showing them to the user

## [0.16.0] - 2026-04-26

### Changed
- Dataset Management page: the "Resources" input on the Create/Edit dataset form no longer requires the user to write JSON
  - Default editor is a guided list of resource cards with URL, Name, Format and Description inputs and Add/Remove controls, mirroring the field set already exposed by the inline resource editor on the dataset detail row
  - An "Advanced (JSON)" toggle still exposes the raw textarea for resources that need fields the simple editor does not show (mimetype, size, …)
  - When editing an existing dataset, each resource is loaded into a card and any non-canonical fields it carries are preserved on save, so a fields-mode round-trip never silently drops data
  - Switching back from JSON to fields is blocked with an inline message when the JSON is invalid, is not an array, or contains non-object items, so the user is never silently downgraded

## [0.15.1] - 2026-04-26

### Fixed
- `example.env` now documents `CKAN_VERIFY_SSL` and `PRE_CKAN_VERIFY_SSL`, the existing settings that toggle TLS certificate verification for the local CKAN and Pre-CKAN instances. Both default to `True` in code, so behavior is unchanged; this only makes the option discoverable for operators running against a self-signed CKAN.

## [0.15.0] - 2026-04-26

### Changed
- Dataset Management page: the "Extras" input on the Create/Edit dataset form no longer requires the user to write JSON
  - Default editor is a guided list of key/value rows with Add/Remove controls, so users unfamiliar with JSON can still attach metadata
  - An "Advanced (JSON)" toggle still exposes the raw textarea for nested or non-text values that the simple fields cannot represent
  - When editing an existing dataset whose extras are a flat primitive map, the editor opens in the guided fields mode pre-populated with the current pairs; nested or non-text values open in the advanced JSON mode instead
  - Switching back from JSON to fields is blocked with an inline message when the JSON is invalid or contains nested/non-text values, so the user is never silently downgraded

### Removed
- UI dead code: the unused client-side `handleSendToPreCkan` flow and the unused `getDatasetTypeBadge` helper in `DatasetManagement` were removed; the Pre-CKAN publish workflow is fully driven from the backend (see 0.14.0)

### Fixed
- Outstanding ESLint warnings in the UI build (`Navigation`, `S3ObjectManager`, `S3Resources`, `Organizations`) were cleaned up so the production build now compiles without warnings

## [0.14.0] - 2026-04-26

### Changed
- `POST /dataset/{dataset_id}/publish` now marks both the local dataset and the Pre-CKAN copy with a `status=submitted` entry in their `extras`, so an Endpoint can tell which of its datasets are pending review and Pre-CKAN reviewers can identify newly submitted datasets in their queue
  - The status is stored as a CKAN-style extra (`{"key": "status", "value": "submitted"}`) alongside any existing extras (`ndp_user_id`, `ndp_group_id`, `ndp_creator_md5`, user-provided extras)
  - Re-publishing a dataset that already had a `status` entry (for example `approved` or `rejected`) replaces it with `submitted`, since this represents a fresh submission to the review queue
  - If creating the dataset in Pre-CKAN fails, the local dataset is left untouched
  - If the local update fails after a successful Pre-CKAN creation, the failure is logged as a warning and the publish still returns success — the Pre-CKAN copy is the source of truth for the review workflow

## [0.13.0] - 2026-04-23

### Added
- Access-request workflow, end-to-end (backend + UI)
  - New `ENABLE_ACCESS_REQUESTS` flag (off by default) so deployments without MongoDB boot unchanged
  - `POST /user/access-requests` lets an authenticated user submit a request with an optional justification; duplicates (existing pending request for the same user) are rejected with 409
  - `GET /user/access-requests` lists pending requests for administrators, with `?status=pending|approved|rejected|all` filter
  - `POST /user/access-requests/{id}/approve` performs the IDP grant using the administrator's own bearer token — either adding the requester to the endpoint group (`grant_type=member`) or also assigning the endpoint admin role (`grant_type=admin`) — and records the decision
  - `POST /user/access-requests/{id}/reject` marks the request as rejected without touching the IDP
  - A new `require_admin` dependency that admits users with either the `ndp_admin` role or the endpoint-specific `{AFFINITIES_EP_UUID}_admin` role
  - A thin client for the NDP AAI API (`add_user_to_group`, `assign_role`, `list_group_members`) so the grant step reuses the administrator's session and no service account is introduced
  - MongoDB-backed persistence in the `access_requests` collection, with the connection string and database name reused from `CatalogSettings` (no new env vars)
  - UI: the AuthGuard 403 screen now offers a "Request access to this Endpoint" button with an optional justification, replaced by a success confirmation once the request is submitted. The user's bearer token is held in memory only for this single call and never persisted to `localStorage`.
  - UI: a new "Access Requests" page, visible in the top nav only to users with the `ndp_admin` or endpoint-scoped `{UUID}_admin` role, lists pending/approved/rejected requests and lets administrators approve (choosing between `member` or `admin` grant, with optional notes) or reject (with optional notes).

## [0.12.0] - 2026-04-22

### Changed
- `ENABLE_GROUP_BASED_ACCESS` now authorizes a user when **any** of the following is true:
  1. The user belongs to one of the groups listed in `GROUP_NAMES` (existing behavior)
  2. The user has the role `ndp_admin`
  3. The user belongs to the group whose name matches `AFFINITIES_EP_UUID`
- When group-based access is disabled the behavior is unchanged — any authenticated user is allowed
- The 403 response body now shows a short user-friendly message ("You do not have permission to access this Endpoint. Please contact the administrator." / "You do not have permission to perform this operation. Please contact the administrator."). The technical details (required role, endpoint group UUID, configured `GROUP_NAMES`) are logged as a backend warning instead of being returned to the user
- `GET /user/info` is now gated by the same authorization rule. When `ENABLE_GROUP_BASED_ACCESS=True`, users that do not satisfy any of the three paths receive 403 Forbidden instead of their profile data, which prevents the UI's AuthGuard from letting them into the app
- The UI credentials login flow now validates the returned token against `/user/info` before storing it, so authorization errors are surfaced at login time rather than after entering the app
- The UI login screen now shows the backend's 403 detail (e.g. "Access forbidden: access to this Endpoint requires …") when the user is not allowed to enter the Endpoint

## [0.11.0] - 2026-04-22

### Added
- Username and password login option on the UI authentication screen
  - New `POST /user/login` endpoint proxies credentials to the configured identity provider and returns the access token plus profile data
  - `AuthGuard` now includes a link below the "Authenticate" button labeled "or use your login / password" that switches the screen to a credentials form (username, password, show/hide toggle); a reciprocal link returns to the access token form
  - On successful login the token is stored in `localStorage` so subsequent requests are authenticated automatically
  - Invalid credentials surface as 401 with the IDP message, IDP outages as 502

## [0.10.11] - 2026-04-13

### Fixed
- `/resources/search` crashed with `AttributeError: 'NoneType' object has no attribute 'lower'` when any resource had `None` values in fields used for filtering (`name`, `url`, `description`, `format`)
  - `dict.get("key", "")` returns the default only when the key is missing; when the key exists with value `None` it returns `None`, breaking the subsequent `.lower()` call
  - Replaced `resource.get("key", "")` with `(resource.get("key") or "")` in all filter branches of `DataCatalogRepository.resource_search`
  - Added regression test covering resources with `None` values across all searchable fields

## [0.10.10] - 2026-04-08

### Fixed
- React asset paths in `index.html` were not rewritten with `ROOT_PATH` prefix
  - Assets like favicon, JS bundles, CSS, and manifest were still referenced as `/ui/...` instead of `{ROOT_PATH}/ui/...`
  - `entrypoint.sh` now rewrites all `"/ui/` references in the built `index.html` at startup
  - Ensures the page loads correctly behind a reverse proxy with any path prefix

## [0.10.9] - 2026-04-08

### Fixed
- Nginx inside the container did not use `ROOT_PATH` for location prefixes
  - `entrypoint.sh` now generates `nginx.conf` dynamically with `ROOT_PATH`-prefixed locations
  - Locations `/ui/`, `/api/`, and `/` become `{ROOT_PATH}/ui/`, `{ROOT_PATH}/api/`, `{ROOT_PATH}/`
  - Also updates the `config.js` script path in the built `index.html` at startup
  - When `ROOT_PATH` is empty, behavior is identical to the previous static config

## [0.10.8] - 2026-04-08

### Fixed
- UI did not use `ROOT_PATH` for API calls when deployed behind a reverse proxy
  - Added `entrypoint.sh` that generates a runtime `config.js` with the `ROOT_PATH` value
  - UI now reads the API base URL from `window.__EP_CONFIG__` instead of build-time env var
  - No rebuild required — just change `ROOT_PATH` in `.env` and restart the container

## [0.10.7] - 2026-04-03

### Fixed
- UI was calling `/general-dataset` endpoint which does not exist in the API
  - Changed UI API client to use the correct `/dataset` path for create, update, and partial update operations
  - Fixes "Failed to create dataset: Not Found" error on the Dataset Management page

## [0.10.6] - 2026-04-03

### Fixed
- JupyterLab Status "Disabled" style now matches Streaming Status style
  - Changed from red error style (`AlertCircle`) to warning style (`MinusCircle`)
  - "Disabled" is not an error — it means the feature is intentionally turned off

## [0.10.5] - 2026-04-03

### Fixed
- Streaming Status card on Dashboard always showed "Connected" even when Kafka is disabled
  - The UI only checked if the API responded, without inspecting the `kafka_connection` field
  - When `KAFKA_CONNECTION=False`, the card now correctly displays "Disabled"
  - Fixed field name mismatch (`host`/`port` vs `kafka_host`/`kafka_port`) that caused "undefined:undefined"

## [0.10.4] - 2026-04-03

### Fixed
- Catalog Status card on Dashboard was permanently stuck on "Checking..." instead of showing "Connected"
  - Status endpoints were incorrectly listed as public, so requests were sent without the auth token
  - The backend requires authentication, causing silent 401 errors that left the status unresolved
  - Removed status endpoints from the public endpoints list so the Bearer token is always sent

## [0.10.3] - 2026-04-02

### Fixed
- Test token now returns a human-readable username ("Test User") in the Dashboard's Current User section
- Test token user no longer includes placeholder groups, matching a realistic no-groups scenario

## [0.10.2] - 2026-04-02

### Removed
- Removed API Connection Status panel from the login screen
  - No longer shows API version, frontend version, or compatibility checks
  - Login screen now displays only the token input form for a cleaner experience
  - Removed version comparison logic and related constants from AuthGuard

## [0.10.1] - 2026-04-02

### Fixed
- Logout now redirects to `/ui/` instead of `/` so the AuthGuard login screen is shown correctly
  - Fixed redirect in `AuthStatus.js` and `Navigation.js`
  - Previously, logout sent users to the server root instead of the UI login screen

## [0.10.0] - 2026-03-30

### Added
- Integrated React frontend (NDP-EP Admin Console) into the monorepo under `ui/`
  - Dashboard, Organizations, Datasets, Services, Search pages
  - S3 bucket/object management
  - Kafka topics and URL resources management
  - AuthGuard with JWT token validation and API version check
- Multi-stage `Dockerfile.allinone` for all-in-one deployment
  - Stage 1: Node 18 builds the React frontend
  - Stage 2: Python 3.13 + nginx + supervisord serves both API and UI
- `nginx.conf` reverse proxy configuration
  - UI served at `/ui/` as static files with SPA routing
  - API accessible at `/` and `/api/` via proxy to uvicorn

### Changed
- `docker-compose.yml` now uses `Dockerfile.allinone` by default
- Removed dependency on external `rbardaji/ndp-ep-frontend` Docker image

## [0.9.0] - 2026-03-12

### Added
- Add `ndp_creator_md5` field for catalog alignment with official NDP catalog

## [0.8.0] - 2026-03-03

### Added
- New endpoint `POST /dataset/{dataset_id}/publish` to copy datasets from local catalog to PRE-CKAN
  - Copies dataset metadata and all associated resources
  - Proper error handling for disabled PRE-CKAN and duplicate names
  - Unit tests for all scenarios
- New `PRE_CKAN_ORGANIZATION` environment variable
  - When set, overrides the owner_org when publishing to PRE-CKAN
  - Required when PRE-CKAN API credentials are tied to a specific organization
  - Local catalog can use any organization; PRE-CKAN uses the configured one

## [0.7.2] - 2026-02-23

### Added
- Create affinity triples when registering datasets and services
  - New `create_affinity_triple()` method in AffinitiesClient
  - Automatic POST to `/affinities` endpoint after dataset registration
  - Automatic POST to `/affinities` endpoint after service registration
  - Creates triples linking datasets/services with their hosting endpoint

## [0.7.1] - 2026-02-19

### Added
- Store Affinities UUID in dataset extras (`ndp_affinity_uuid`) after registration
- Store Affinities UUID in service extras (`ndp_affinity_uuid`) after registration
- UUIDs enable cross-referencing between local catalog and Affinities API

## [0.7.0] - 2026-02-18

### Added
- NDP Affinities integration for automatic registration of datasets and services
  - New configuration: `AFFINITIES_ENABLED`, `AFFINITIES_URL`, `AFFINITIES_EP_UUID`, `AFFINITIES_TIMEOUT`
  - AffinitiesClient module for async HTTP communication with Affinities API
  - Automatic dataset registration in Affinities on `POST /dataset`
  - Automatic service registration in Affinities on `POST /services`
  - Automatic endpoint relationships created for datasets and services
  - Non-blocking integration: Affinities errors don't affect main operations
  - Documentation: `docs/affinities-integration.md`

## [0.6.1] - 2026-02-12

### Changed
- Version bump for Docker image release

## [0.6.0] - 2026-02-02

### Added
- MongoDB full-text search with text indexes
  - Text index on `title`, `tags`, and `notes` fields with weighted relevance (title: 10, tags: 5, notes: 1)
  - Uses MongoDB `$text` operator for efficient full-text search
  - Relevance-based sorting using `$meta: "textScore"`
  - 10-100x performance improvement over regex-based search for large datasets
  - Built-in stemming, stop words, and case-insensitive matching
  - Backward compatible with Solr-style field queries (`field:value`)
- Comprehensive test suite for MongoDB full-text search functionality

### Changed
- MongoDB `package_search` now uses `$text` operator for simple text queries instead of regex
- Search results are sorted by relevance score when using full-text search

## [0.5.3] - 2025-12-27

### Changed
- Renamed `ENABLE_ORGANIZATION_BASED_ACCESS` to `ENABLE_GROUP_BASED_ACCESS`
- Added `GROUP_NAMES` environment variable for comma-separated list of allowed groups
- Authorization now checks if user belongs to any group in `GROUP_NAMES` instead of single organization
- Backward compatibility maintained with function aliases

## [0.5.2] - 2025-12-22

### Added
- Installation script (`install.sh`) for fresh Ubuntu systems
  - Interactive configuration prompts
  - Automatic Docker installation
  - Environment file generation with overwrite protection
- Infrastructure services reporting to federation metrics
  - `jupyterlab_enabled` + `jupyterlab_url`
  - `kafka_enabled` + `kafka_host` + `kafka_port`
  - `s3_enabled`
  - `pre_ckan_enabled`
- Docker Compose profiles for optional services
  - `mongodb`: MongoDB + Mongo Express
  - `kafka`: Kafka + Zookeeper + Kafka UI
  - `s3`: MinIO
  - `jupyter`: JupyterLab
  - `pelican`: Pelican Federation services
  - `frontend`: NDP-EP Frontend
  - `full`: All services

### Changed
- Docker Compose now starts only the API by default
- Healthcheck endpoint changed from `/status/` to `/` (status requires auth)

## [0.5.1] - 2025-12-22

### Fixed
- Added authentication requirement to all `/status` endpoints
- Fixed tests for `resource_patch` method in base repository
- Fixed SSL verification test to use explicit configuration

## [0.5.0] - 2025-12-08

### Added
- Resource management endpoints by ID only (no dataset_id required)
  - `GET /resource/{resource_id}` - Get resource by ID
  - `PATCH /resource/{resource_id}` - Update resource by ID
  - `DELETE /resource/{resource_id}` - Delete resource by ID
- Resource search endpoint with filtering capabilities
  - `GET /resources/search` - Search resources across all datasets
  - Supports filters: `q` (general), `name`, `url`, `format`, `description`
  - Pagination with `limit` and `offset` parameters
  - Results include parent dataset context (dataset_id, dataset_name, dataset_title)
- MongoDB-optimized `resource_search` implementation in repository layer

## [0.4.1] - 2025-12-07

### Added
- SSL verification toggle for CKAN connections
  - `CKAN_VERIFY_SSL` environment variable (default: True)
  - `PRE_CKAN_VERIFY_SSL` environment variable (default: True)
  - Allows disabling SSL certificate verification for self-signed certificates
  - Fixes SSL errors when connecting to CKAN instances with self-signed certs

### Changed
- Refactored URL normalization into `_normalize_url` helper method in ckan_settings

## [0.4.0] - 2025-11-27

### Added
- New endpoint to delete individual resources from a dataset
  - `DELETE /dataset/{dataset_id}/resource/{resource_id}` removes a single resource
  - Dataset and other resources remain intact
  - Supports both local and pre_ckan server parameters
  - New service function `delete_resource()` in dataset_services
- New endpoint to partially update individual resources (PATCH)
  - `PATCH /dataset/{dataset_id}/resource/{resource_id}` updates only specified fields
  - Supports updating name, url, description, format
  - New `resource_patch` method in repositories (CKAN and MongoDB)
  - New service function `patch_resource()` in dataset_services

### Fixed
- ROOT_PATH now properly propagates to Swagger UI requests (fixes #23)
  - Added servers configuration to OpenAPI schema when ROOT_PATH is set

### Documentation
- Added link to "Adding New Catalog Backends" documentation in README (fixes #22)

## [0.3.4] - 2025-11-27

### Fixed
- Use purge instead of delete for CKAN datasets and organizations
  - Changed `package_delete` to use `dataset_purge` for permanent deletion
  - Changed `organization_delete` to use `organization_purge` for permanent deletion
  - CKAN's soft-delete left datasets in database, preventing organization deletion
  - Now datasets and organizations are completely removed, enabling proper cleanup

## [0.3.3] - 2025-11-27

### Fixed
- Fixed AttributeError in service routes when using CKAN backend
  - Service routes accessed `repository.ckan_instance` but CKANRepository stores client as `self.ckan`
  - Affected endpoints: POST /services, PUT /services/{id}, PATCH /services/{id}

## [0.3.2] - 2025-11-12

### Fixed
- **Critical: MongoDB organization search compatibility** - Fixed search by organization name in MongoDB backend
  - MongoDB stores `owner_org` as UUID, but CKAN allows searching by organization name
  - Added automatic organization name → UUID resolution in all search paths (q, fq, fq_list)
  - Ensures `{"owner_org": "services"}` searches work identically in MongoDB and CKAN backends
  - Maintains full backward compatibility with existing code

## [0.3.1] - 2025-11-12

### Fixed
- Fixed MongoDB repository `owner_org` expansion issue where services and datasets showed `owner_org: null` in search results
  - Added automatic expansion of `owner_org` UUID to full `organization` object in `package_search` method
  - Maintains CKAN API compatibility by providing organization details (id, name, title, description) in search results
  - All services now correctly display their associated organization

### Added
- Sample data seeding script (`seed_sample_data.py`) for development and demo purposes
  - Creates 4 organizations (services, marine-research, climate-monitoring, biodiversity-lab)
  - Seeds 5 real public API services (Dog Breed, Cat Facts, JSONPlaceholder, Public Holidays, Open-Meteo Weather)
  - Creates S3 buckets and uploads sample data files with real content
  - Includes cleanup functionality to avoid duplicates
- CHANGELOG.md to track all project changes following Keep a Changelog format

## [0.3.0] - 2025-01-10

### Added
- Pelican federation integration for data discovery across federated origins
  - New Pelican repository (`api/repositories/pelican_repository.py`) for federation access
  - Pelican service layer for federation operations
  - Pelican API endpoints for federated dataset discovery
  - Unified download helper with Pelican support
  - Pelican configuration variables and conditional route integration
  - Pelican Origin configuration file
  - Docker Compose services for Pelican federation (origin, cache, director)
- Comprehensive test suite for Pelican routes
- Pelican federation integration documentation

### Changed
- Docker Compose stack now includes Pelican services (optional)
- Enhanced metrics payload with catalog data and configurable interval
- Added `ep_name` and `metrics_interval` to status endpoint
- Updated metrics format for better observability

### Fixed
- Implemented repository pattern for search functions to support MongoDB
- Ensured `LOCAL_CATALOG_BACKEND` is respected in service routes
- Ensured 'services' organization exists on startup

## [0.2.0] - 2024-12-15

### Added
- FastAPI-MCP integration for AI agent communication
  - MCP (Model Context Protocol) server mounted at `/mcp` endpoint
  - AI agents can discover and invoke all API operations automatically
  - Full API surface exposed as MCP tools
- AI agent integration documentation
- Complete Docker Compose stack with web interfaces
  - MongoDB Express for database management
  - Kafka UI for stream monitoring
  - MinIO Console for S3 storage management
  - JupyterLab for interactive data analysis
- Background metrics task with configurable interval
  - System metrics (CPU, memory, disk, public IP)
  - Catalog statistics (dataset count, service count)
  - Service registry information
  - Automatic posting to federation metrics endpoint

### Changed
- Updated Python base image from 3.9 to 3.13
- Improved metrics task with enhanced payload structure
- Updated README with new configuration and metrics information
- Added configurable API root path for flexible deployment

### Fixed
- Full metrics handler updated to support new system metrics format

## [0.1.0] - 2024-11-01

### Added
- Initial release of NDP-EP API
- Repository pattern architecture for catalog abstraction
  - Abstract base repository (`DataCatalogRepository`)
  - CKAN repository implementation
  - MongoDB repository implementation
  - Factory pattern for runtime backend selection
- Three catalog types support:
  - Local catalog (configurable: CKAN or MongoDB)
  - Global catalog (CKAN, read-only)
  - PreCKAN catalog (CKAN staging)
- Core API functionality:
  - Dataset management (CRUD operations)
  - Resource management (URL, S3, Kafka)
  - Organization management
  - Service registry
  - Federated search across catalogs
- S3 integration with MinIO
  - Bucket management
  - Object upload/download
  - Presigned URLs
  - Metadata operations
- Kafka integration
  - Topic-based dataset ingestion
  - Stream metadata management
- Authentication and authorization
  - Bearer token authentication
  - Organization-based access control
  - User information endpoints
- Health checks and status endpoints
- Comprehensive API documentation (OpenAPI/Swagger)
- Docker support with multi-stage builds
- Logging with rotation
- Environment-based configuration

### Infrastructure
- Docker Compose setup for local development
- MongoDB backend for local catalog
- MinIO for S3-compatible storage
- Apache Kafka for streaming data
- Zookeeper for Kafka coordination

---

## Version Schema

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality in a backwards compatible manner
- **PATCH** version: Backwards compatible bug fixes

## Categories

Changes are grouped into the following categories:
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes
