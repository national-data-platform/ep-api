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
- Defaults below are the defaults **in the code** (`api/config/`). `example.env`
  sets several of them differently (it is written as a demo with most features
  on), and the installer writes its own values; see
  [installing-with-the-script.md](installing-with-the-script.md).
- Settings are read once, when the API starts. Changing one needs a container
  restart (`docker compose up -d` recreates it when `.env` changed).

### Where the values are read from

Most variables are read by `pydantic-settings` classes in `api/config/`, which
take them from the process environment and, failing that, from a `.env` file in
the working directory. A few are read **only from the process environment**:

- `PELICAN_*` (including `PELICAN_ENABLED`) and `NETBIRD_*`, read with
  `os.getenv`;
- `OTEL_*` (its settings class does not read `.env`);
- the values `entrypoint.sh` uses to generate the nginx and UI configuration
  (`ROOT_PATH`, `AFFINITIES_EP_UUID`, `OIDC_*`).

Inside the container this makes no difference: `docker-compose.yml` loads `.env`
into the container's environment (`env_file: .env`). It matters when uvicorn is
run directly from a checkout, where those variables must be exported in the
shell.

### Minimum to get started (connect to the National Data Platform)

You really only need to set:

- `AUTH_API_URL` → the platform's AAI (so logins/roles work).
- `LOCAL_CATALOG_BACKEND` → `none` for an Endpoint that stores nothing locally,
  or `mongodb`/`ckan` plus that backend's variables.
- `CKAN_LOCAL_ENABLED=True` → if this EP should allow publishing (not read-only);
  `False` with `LOCAL_CATALOG_BACKEND=none`.
- `ORGANIZATION`, `EP_NAME` → how your EP identifies itself.
- `TEST_TOKEN` → blank in any deployment reachable by others (see below).

Everything else turns optional features on/off.

---

## Docker Compose

#### `EP_API_PORT`
*Optional · default: `8002`.*
Host port the `api` service publishes the container's port 80 on
(`"${EP_API_PORT:-8002}:80"` in `docker-compose.yml`). It is read by Docker
Compose, not by the API, so it must be in the shell environment or in the
`.env` next to `docker-compose.yml` when you run `docker compose`. The installer
takes it from its "Port to publish the Endpoint on" prompt (or `--ep-api-port`)
and passes it on the `docker compose` command line only; it does not write it to
`.env`. A later `docker compose up` run by hand therefore publishes on 8002
unless `EP_API_PORT` is set again (with `--no-start` the installer prints the
full command instead of running it).

---

## General / API

#### `ROOT_PATH`
*Optional · default: empty (served at `/`).*
URL path prefix when the EP runs behind a reverse proxy at a sub-path (e.g.
`/ep-api`). With it set, the UI is served at `${ROOT_PATH}/ui/` and the API at
`${ROOT_PATH}/` (and `${ROOT_PATH}/api/`). nginx passes the full path to the API
and FastAPI's `root_path` removes the prefix (since 0.34.45), so redirects keep
it. Write it with a leading slash and no trailing slash: `/ep-api`, not
`ep-api/`.
**Where:** match the path your reverse proxy mounts the EP at; leave empty if it
is served at the domain root.

#### `ORGANIZATION`
*Optional · default: `Unknown Organization`.*
Display name of the organization running this Endpoint (shown in the UI and
reported to Federation). **Where:** you choose it.

#### `EP_NAME`
*Optional · default: `Unknown EP`.*
Display name of this Endpoint (UI + Federation registry). **Where:** you choose it.

#### `IS_PUBLIC`
*Optional · default: `True` (the installer writes `False` unless the Federation
registration says the Endpoint is listed).*
Whether this Endpoint reports to the Federation. With `True` the periodic
metrics report is POSTed to `METRICS_ENDPOINT`; with `False` it is still
collected and written to the log, and nothing leaves the Endpoint. It is also
shown in `GET /status/`. It does not control who can read the Endpoint's data.
**Where:** `True` only for an Endpoint registered with the Federation; the
installer derives it from the "List this Endpoint on the platform?" answer.

#### `USE_JUPYTERLAB` / `JUPYTER_URL`
*Optional · defaults: `False` / `https://jupyter.org/try-jupyter/lab/`.*
Show a "JupyterLab" link in the UI and where it points. `USE_JUPYTERLAB=True`
also mounts `GET /status/jupyter` and adds the URL to `/status/` and the metrics
report; the API never calls it. **Where:** set `USE_JUPYTERLAB=True`
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
identity, groups and **roles**: every authenticated request sends
`POST AUTH_API_URL` with `{"token": "<token>"}`. This is the single source of
authentication. The scheme and host of this URL are also used for
username/password login (`<host>/user/login`) and for the AAI calls that grant
access requests (`<host>/group/add-user`, `<host>/role/assign`).
**Where:** your NDP/AAI administrator. For the central platform use the default;
for a self-hosted AAI use its `…/information` URL.

#### `TEST_TOKEN`
*Optional · dev only · default: `testing_token`.*
A fixed token the EP accepts without contacting AAI. **Whoever presents it is
signed in as a platform administrator** (`roles: ["ndp_admin"]`, `sub:
test_user`): it passes every role check and the group gate. The default value is
public (it is in this repository and in `example.env`), so an Endpoint left at
the default can be administered by anyone who can reach it.
**Where:** you set it for local development. **Set it blank (`TEST_TOKEN=`) on
any Endpoint others can reach**; a blank value can never match, because a
bearer token is never empty.

#### `ENABLE_GROUP_BASED_ACCESS`
*Optional · default: `False`.*
If `True`, an extra gate applies on top of the role model to `/user/info`
(the UI's entry check), every write route, every `/s3/*` route and every
`/pelican/*` route: the user must hold `ndp_admin`, or belong to the group named
`AFFINITIES_EP_UUID`, or belong to one of `GROUP_NAMES`. Catalog searches stay
public. **Where:** the installer turns it on when the Federation registration
provides a group.

#### `GROUP_NAMES`
*Optional · default: empty.*
Comma-separated list of the Endpoint's groups (e.g. `ndp_ep/ep-123`). Used in
three places:

- the group gate above (membership in any of them passes; matching is
  case-insensitive and ignores leading/trailing slashes);
- the per-Endpoint role names: `group:<entry>:admin|writer|editor|viewer` is
  accepted for each entry (see [roles-and-permissions.md](roles-and-permissions.md));
- access-request approval (since 0.34.46): the user is added to, and given
  their role on, the **first** entry.

Empty with the gate on lets in only `ndp_admin` holders and members of the
`AFFINITIES_EP_UUID` group. **Where:** the installer writes the group the
Federation created for the Endpoint (`ndp_ep/ep-<config-id>`); otherwise ask
your AAI administrator.

> **Roles** (`viewer` / `writer` / `admin`) are **not** set here — they travel in
> the token issued by AAI. See [roles-and-permissions.md](roles-and-permissions.md).

---

## Identity provider sign-in (optional, off by default)

By default the UI login screen offers two ways in: paste an access token, or
type a username and password. Both assume the user holds a credential that
lives in the realm itself.

Users who arrive through a **federated provider** configured on the realm —
CILogon (institutional credentials), EarthScope, ORCID — do not. They have no
password in the realm, so the username/password form cannot work for them, and
their only route in is to sign in on the platform's own site, find their access
token and paste it by hand.

Turning this on adds a **third** button that sends the user to the identity
provider's own login page, where those providers appear. It uses the OAuth
Authorization Code flow with PKCE against a **public** client, so no client
secret is shipped with the Endpoint.

The other two methods are unchanged and remain available either way.

#### `OIDC_ENABLED`
*Optional · default: `False`.*
Master switch. While `False`, the login screen behaves exactly as before and
none of the values below are read. **Where:** you decide.

#### `OIDC_ISSUER`
*Required when `OIDC_ENABLED=True`.*
The realm URL, e.g. `https://idp.nationaldataplatform.org/realms/NDP`. The
authorization, token and userinfo endpoints are read from this realm's OpenID
discovery document, so no provider-specific URL is hardcoded — moving from a
local Keycloak to production is just a change of this value.
**Where:** your AAI/Keycloak administrator.

#### `OIDC_CLIENT_ID`
*Required when `OIDC_ENABLED=True`.*
The client registered for **this** Endpoint (see the requirements below).
**Where:** your AAI/Keycloak administrator.

#### `OIDC_SCOPE`
*Optional · default: `openid profile email`.*

#### `OIDC_BUTTON_LABEL` / `OIDC_HELP_TEXT`
*Optional · defaults: `Sign in with your identity provider` / empty.*
Wording for the button and the line under it. The defaults are
provider-neutral on purpose: only the deployment knows which providers its
realm offers. Naming providers the realm does **not** have is worse than
saying nothing, so `OIDC_HELP_TEXT` shows no second line while empty.

### What your identity provider administrator must register

1. **A public client with PKCE (S256).** Public rather than confidential so
   that no client secret has to be distributed with the Endpoint, which is
   self-hosted by many institutions.
2. **This deployment's callback URL** as a valid redirect URI on that client:
   `<scheme>://<host>[:<port>]<ROOT_PATH>/ui/auth/callback` — for example
   `https://my-endpoint.example.org/ep-api/ui/auth/callback`. The Endpoint
   derives this from the browser's address and `ROOT_PATH`, so you never
   configure it, but it must match what is registered.
3. **The `sub` claim in access tokens.** `AUTH_API_URL` looks the user up by
   `sub`. Since Keycloak 24 that claim comes from the built-in `basic` client
   scope, and a realm imported from an older export may not have `basic` among
   its default scopes — in which case a freshly created client silently mints
   tokens without `sub`. Assign the scope to the client explicitly.

### Two things that commonly go wrong

**`OIDC_ISSUER` and `AUTH_API_URL` must point at the same identity provider.**
The token is minted by one and validated by the other. If they disagree, the
user's `sub` will not exist on the validating side and sign-in fails at the
last step — after a successful login, which makes it look like a credentials
problem when it is not.

**The UI must be served over https.** Browsers only expose the crypto API that
PKCE needs in secure contexts. On a plain-http or bare-IP deployment the button
is shown **disabled** with an explanation rather than silently falling back to
the weaker `plain` challenge method; the other two sign-in methods still work
there. `localhost` counts as a secure context, so an SSH tunnel is enough for
testing.

---

## Local catalog (where this EP stores its data)

#### `LOCAL_CATALOG_BACKEND`
*Required · default: `ckan`.*
Backend for **this EP's own** catalog: `ckan`, `mongodb` or `none`. (The global
and Pre-CKAN catalogs always use CKAN regardless.) `none` is an Endpoint that
stores nothing locally: no MongoDB or CKAN is needed, the registration, update,
delete and resource routes are not mounted, `/ready` reports the local catalog
as `disabled`, and the metrics report counts no datasets or services. It still
authenticates users, searches the global catalog and reports to the Federation.
The value is case-insensitive; anything else makes every local-catalog call fail
with "Unsupported catalog backend". **Where:** you choose — `none` is the
installer's default, `mongodb` is the simplest to self-host, `ckan` if you
already run a CKAN.

#### `CKAN_LOCAL_ENABLED`
*Optional · default: `False`.*
Master switch for the local catalog, for **any** backend. With `False` the
routes that write to it (create/update/delete organizations, datasets,
resources) and the resource routes are not mounted, `GET /search?server=local`
answers 400, `/ready` does not probe the local catalog, and the `services`
organization is not created at startup. *(The name keeps "CKAN" for historical
reasons; it applies to MongoDB too.)* **Where:** set `True` if this EP should
accept publishing; keep `False` with `LOCAL_CATALOG_BACKEND=none`.

### CKAN backend — only if `LOCAL_CATALOG_BACKEND=ckan`

#### `CKAN_URL`
*Required (CKAN backend) · default: `http://localhost:5000`.*
Base URL of your CKAN instance. **Where:** your CKAN deployment URL.

#### `CKAN_API_KEY`
*Required (CKAN backend) · default: `your-api-key` (a placeholder).*
API key used to write to CKAN. The metrics report includes whether a key other
than the placeholder is set (`ckan_api_key_configured`), never the key itself. **Where:** in CKAN, log in → your user profile →
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
MongoDB connection URI for the local catalog, and also for the access-request
store whatever the catalog backend is. **Where:** your MongoDB. With the
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
*Required only if `PRE_CKAN_ENABLED=True`. Code defaults: `https://ndp-test.sdsc.edu/catalog2`,
empty, `True`, empty.*
URL (`http://` is prepended when it has no scheme), API key (same place as
`CKAN_API_KEY`, but on the Pre-CKAN instance), TLS verification, and the
organization all staged datasets are published under (overrides their
`owner_org`). `/ready` reports Pre-CKAN `disabled` while the URL or the key is
empty, and reports `organization_configured`. **Where:** a registered Endpoint
gets all four from the Federation registration through the installer
(`PRE_CKAN_ORGANIZATION=ep-<config-id>`); otherwise from whoever operates your
Pre-CKAN.

---

## S3 / object storage (MinIO)

#### `S3_ENABLED`
*Optional · default: `False`.*
Mounts the `/s3/buckets/…` and `/s3/objects/…` routes (all of them require the
writer role) and the **S3 Management** tool in the UI. Unrelated to `POST /s3`,
which registers a catalog dataset pointing at an S3 URL and is controlled by
`CKAN_LOCAL_ENABLED`. Setup: [minio-setup.md](minio-setup.md).

#### `S3_ENDPOINT`
*Required if `S3_ENABLED=True` · default: `localhost:9000`.*
`host:port` of the S3-compatible service, reachable from inside the container,
without a scheme. **Where:** your MinIO/S3 endpoint. With the bundled Compose
service (`--profile s3`) use `minio:9000`; that service runs `pgsty/silo`, a
community fork of MinIO, published on the host as 9002 (API) and 9003
(console).

#### `S3_ACCESS_KEY` / `S3_SECRET_KEY`
*Required if `S3_ENABLED=True` · dev defaults: `minioadmin` / `minioadmin123`.*
Credentials for the S3 service. **Where:** your MinIO/S3 admin console (Access
Keys). The bundled service is started with `minioadmin` / `minioadmin123`
(set in `docker-compose.yml`); change both places together for anything beyond
development.

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
Declares that a Kafka broker is available. It turns on the Kafka check in
`/ready` (a producer connection to the broker) and is reported in `/status/` and
the metrics report together with host and port. The API itself does not create
topics or consume messages; `POST /kafka` (controlled by `CKAN_LOCAL_ENABLED`)
only stores a dataset describing a topic.

#### `KAFKA_HOST` / `KAFKA_PORT`
*Required if `KAFKA_CONNECTION=True` · defaults: `localhost` / `9092` (an empty
value falls back to these).*
Kafka broker address as seen from inside the container. **Where:** your broker.
With the bundled Compose service (`--profile kafka`) use `kafka` and `9093`.
That broker is also published on the host as `9094` (its `9092` listener) and
`9095` (its `9093` listener), for clients outside Docker.

#### `KAFKA_PREFIX`
*Optional · default: `data_stream_`.*
Topic prefix for derived streams. The API does not apply it; it only returns
it from `GET /status/kafka-details` for clients that create streams.

#### `MAX_STREAMS`
*Optional · default: `10`.*
Per-user quota of derived streams. Like `KAFKA_PREFIX`, the API only returns
it from `GET /status/kafka-details` (`null` when unlimited); enforcing it is up
to the client that creates streams. A non-negative integer, or blank for
unlimited; a negative or non-integer value stops the API from starting.

---

## Affinities integration

#### `AFFINITIES_ENABLED`
*Optional · default: `False`.*
When `True` (and `AFFINITIES_URL` and `AFFINITIES_EP_UUID` are both set),
datasets and services created with `POST /dataset` and `POST /services` are
registered in Affinities (non-blocking — the EP keeps working if Affinities is
down). The installer always writes `False`.

#### `AFFINITIES_URL`
*Required if `AFFINITIES_ENABLED=True`.*
Base URL of the Affinities API (e.g. `http://affinities-api:8000`). **Where:** the
platform's Affinities URL, or your local one.

#### `AFFINITIES_EP_UUID`
*Required if `AFFINITIES_ENABLED=True` · default: empty.*
This Endpoint's UUID inside Affinities. Beyond the Affinities integration, the
value is used in several places even with `AFFINITIES_ENABLED=False`:

- **Roles:** `group:<uuid>:<tier>`, `group:ndp_ep/<uuid>:<tier>`,
  `group:ndp_ep/ep-<uuid>:<tier>` and the legacy `<uuid>_admin` are accepted
  as per-Endpoint roles (see [roles-and-permissions.md](roles-and-permissions.md)).
- **Group gate:** members of the group named `<uuid>` pass
  `ENABLE_GROUP_BASED_ACCESS`.
- **Access requests:** approval grants membership and role on this group when
  `GROUP_NAMES` is empty (since 0.34.46; up to 0.34.45 it was the only group
  used, and approval answered 503 without it).
- **Pelican events:** fallback client id for `GET /pelican/subscribe` when
  `PELICAN_EVENT_CLIENT_ID` is empty.
- **UI:** passed to the UI in `config.js`.

**Where:** the endpoint's `uid` in Affinities — list/create it via `GET`/`POST /ep`
on the Affinities API, or from the **Endpoints** page of the Affinities web app.
See [affinities-integration.md](affinities-integration.md). The installer does
not set it.

#### `AFFINITIES_TIMEOUT`
*Optional · default: `30`.*
HTTP timeout (seconds) for Affinities calls.

---

## Federation (metrics reporting)

#### `METRICS_ENDPOINT`
*Optional · default: `https://federation.ndp.utah.edu/metrics/`.*
The Federation endpoint this EP periodically reports health/usage metrics to,
which is how the EP becomes discoverable in the federation. Posted to only when
`IS_PUBLIC=True`. **Where:** the installer writes `<federation-url>/metrics/`
for the Federation it was pointed at; otherwise the platform's Federation
`/metrics/` URL, or your local Federation when self-hosting. Details in
[architecture/federation-and-metrics.md](architecture/federation-and-metrics.md).

#### `METRICS_INTERVAL_SECONDS`
*Optional · default: `3300` (55 min).*
How often metrics are collected (and, with `IS_PUBLIC=True`, reported). One
worker of the four does this (the leader, see
[architecture/overview.md](architecture/overview.md#9-background-work)).

#### `NETBIRD_ENABLED` / `NETBIRD_IP` / `NETBIRD_GROUP`
*Optional · defaults: empty. Read from the process environment only.*
Deployment metadata added to the metrics report so the platform can see the
Endpoint's NetBird connectivity: `netbird_enabled` (true for `1`, `true`,
`yes`, `on`), `netbird_ip` and `netbird_group`. Nothing is added when all three
are empty. The Endpoint does not use NetBird itself. **Where:** whoever runs
the host's NetBird client; the installer does not set them.

---

## Pelican federation (external data access)

All `PELICAN_*` variables are read with `os.getenv`, so they come from the
process environment only (see [Where the values are read from](#where-the-values-are-read-from)).

#### `PELICAN_ENABLED`
*Optional · default: `False`.*
Mounts the `/pelican/*` routes: browsing/downloading from Pelican federations
(OSDF, etc.) and importing a Pelican object into a local dataset. Every route
requires at least the viewer role; `POST /pelican/import-metadata` requires
writer.

#### `PELICAN_FEDERATION_URL`
*Optional · default: empty (uses OSDF).*
Default Pelican federation, format `pelican://host` (e.g. `pelican://osg-htc.org`).
**Where:** the federation you target; leave empty for OSDF.

#### `PELICAN_DIRECT_READS`
*Optional · default: `False`.*
Read straight from origin servers instead of caches. **Where:** keep `False` for
better performance unless you have a reason.

#### `PELICAN_MAX_READ_BYTES`
*Optional · default: `10485760` (10 MiB).*
Largest object `GET /pelican/read` returns inline. That endpoint puts the
contents in the response body, so this caps what a single request can pull into
the API's memory; a larger object is refused with 413 and must be fetched with
`/pelican/download`. A non-numeric or non-positive value falls back to the
default. **Where:** raise it only if your callers genuinely read larger objects
inline.

#### `PELICAN_EVENT_SERVER_URL`
*Optional · default: the CHTC event server.*
Event server backing `GET /pelican/subscribe`, as an `http(s)` or `ws(s)` URL.

#### `PELICAN_EVENT_CLIENT_ID`
*Optional · default: `AFFINITIES_EP_UUID`.*
Identity this Endpoint presents to the event server, used for callers that do
not bring their own. **Must be unique**: two subscribers sharing an id are
served by splitting the events between them, so each sees only a fraction. Must
not contain `/`, since it is one segment of the STOMP destination. When neither
this, the Endpoint UUID, nor a caller-supplied id is available,
`GET /pelican/subscribe` answers 503 saying so. **Where:** leave empty unless
one host runs several Endpoints.

#### `PELICAN_EVENT_USERNAME` / `PELICAN_EVENT_PASSWORD`
*Optional · default: empty. Set both or neither.*
Credentials the event server checks against its own store — unrelated to the
Endpoint token. Used for callers that do not supply their own. Temporary: they
are due to be replaced by an access token issued for NDP.

> **Callers may override all three.** `GET /pelican/subscribe` accepts
> `client_id`, `username` and `password` as query parameters, and the same
> three as the `X-Pelican-Event-Client-Id`, `X-Pelican-Event-Username` and
> `X-Pelican-Event-Password` headers, which win. Prefer the headers: a query
> string is written to the access logs of both uvicorn and nginx, so a password
> passed that way lands on disk in plain text. Credentials are taken as a pair —
> supplying only a username is refused rather than borrowing the Endpoint's
> password. Subscribers presenting the same client id share one upstream
> connection and each receive every event on it.

#### `PELICAN_EVENT_VIRTUAL_HOST`
*Optional · default: `playground`.*
STOMP virtual host sent in the CONNECT frame.

#### `PELICAN_EVENT_HEARTBEAT_MS`
*Optional · default: `10000`. Minimum 1000.*
Liveness interval. A non-numeric or too-small value falls back to the default.

---

## Remote execution (Rexec)

#### `REXEC_CONNECTION`
*Optional · default: `False`.*
Mounts `GET /status/rexec` (writer role), which returns
`REXEC_DEPLOYMENT_API_URL` to the UI. The API does not call that service.

#### `REXEC_DEPLOYMENT_API_URL`
*Required if `REXEC_CONNECTION=True`.*
URL of the Remote Execution Deployment API. **Where:** from whoever operates that
service.

---

## Access requests

#### `ENABLE_ACCESS_REQUESTS`
*Optional · default: `False`.*
Enable the access-request workflow (a user requests access; an admin
approves/rejects). While `False` every `/user/access-requests` route answers
503. **Requires MongoDB** reachable via `MONGODB_CONNECTION_STRING` (database
`MONGODB_DATABASE`), whatever the catalog backend is. Approval calls the AAI
with the approving administrator's token and grants membership and role on the
first `GROUP_NAMES` entry, or on `AFFINITIES_EP_UUID` when `GROUP_NAMES` is
empty (since 0.34.46); with neither it answers 503.
**Where:** turn on if you want self-service access requests; the installer
installs MongoDB for it when the catalog does not provide one.

#### `ACCESS_REQUESTS_COLLECTION`
*Optional · default: `access_requests`.*
MongoDB collection used to store access requests.

---

## Telemetry — OpenTelemetry (advanced)

Read from the process environment only: the settings class for these does not
read `.env` (see [Where the values are read from](#where-the-values-are-read-from)).

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
