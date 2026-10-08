# Installing an Endpoint with the script

The quickest way to stand up an NDP Endpoint is the installer. It registers the
Endpoint with the NDP Federation, sets up its catalog, and starts it — from a
single command:

```bash
bash <(curl -fsSL https://bit.ly/ndp-ep)
```

`bit.ly/ndp-ep` redirects to the installer on the `main` branch. The command
clones the repository, then walks you through a few questions and brings the
Endpoint up. Nothing is written or started until you confirm.

> Use the `bash <(...)` form, not `curl ... | bash`. The `<(...)` form keeps the
> prompts interactive so you can answer them.

## Before you start

- **Docker** and the Docker Compose plugin, and permission to use them.
- **git**, **curl**, **python3** (present on most systems).
- **An NDP access token**, if you want the Endpoint listed in the Federation.
  Sign in at [nationaldataplatform.org](https://nationaldataplatform.org/) and
  copy the token from your user panel. The token is sent only to the Federation
  and is never stored.

## What the installer asks

Run it and answer the prompts. Each has a short explanation on screen; the main
choices are:

1. **Configuration id** — leave blank the first time and it offers to register.
   With an id, it offers to keep your answers in the Federation registration
   (this needs your token) so a later run can reuse them.
2. **Local catalog** — where this Endpoint stores its datasets, or whether it
   stores any at all (see below).
3. **S3 object storage** — off by default. Answer yes and choose between a
   MinIO installed alongside the Endpoint and an S3-compatible service you
   already run (see [S3 object storage](#s3-object-storage)).
4. **Register with the Federation** (only without a configuration id) —
   answer yes and give your token; this is what lists the Endpoint on the
   platform and creates its Keycloak group, which the group-based access
   control is keyed on. Registering asks for the organization, Endpoint name,
   a contact email, whether to list the Endpoint on the platform, and the
   optional features below. Answer no for a standalone Endpoint: you are asked
   only for the organization and Endpoint name, it will not be listed, and it
   reports nothing back.
5. **Endpoint port** — the first free port from 8002 is offered. With a CKAN
   installed by the script, its three ports and sysadmin name follow.
6. **Authentication service** — the AAI URL; the default is the National Data
   Platform's.
7. **Access requests** — off by default. Answer yes to let people without
   access ask for it from the login screen and have an administrator approve
   it in the UI. The requests are stored in MongoDB: the one the catalog uses,
   or a MongoDB installed for this alone when the catalog is not MongoDB.

Press Enter at any prompt to accept the value in brackets.

When it finishes you'll see `Endpoint healthy` and a URL like
`http://localhost:8002/ui/`.

Keep the configuration id it prints — re-running with `--config-id <id>`
reproduces the same Endpoint without registering again.

## Catalog options

The installer offers five answers at the "Which local catalog should this
Endpoint use?" prompt.

### 1. None — nothing is stored locally

The default, and the quickest Endpoint to stand up: no MongoDB, no CKAN,
nothing installed. It authenticates users, searches the platform's global
catalog, serves its UI and reports to the Federation, which is what most
Endpoints are asked to do. Nothing can be published to it — the registration
and update routes are not offered at all — and a catalog can be added later by
running the installer again.

<!-- video: no local catalog -->
📹 _Recording: coming soon_

### 2. MongoDB, installed by the script

The simplest option. The installer starts a MongoDB alongside the Endpoint — no
external services, nothing to prepare.

<!-- video: MongoDB installed by the script -->
📹 _Recording: coming soon_

### 3. MongoDB, one you already run

Point the Endpoint at an existing MongoDB instead of starting one. You'll be
asked for a connection string reachable from inside the Endpoint container (a
MongoDB on the host is `mongodb://host.docker.internal:27017`).

<!-- video: existing MongoDB -->
📹 _Recording: coming soon_

### 4. CKAN, installed by the script

The fullest option. The installer clones CKAN, builds and starts it, creates a
sysadmin and mints an API token for the Endpoint. This takes several minutes the
first time (CKAN, Solr and Postgres). Ports that clash with other services are
avoided automatically — press Enter to accept the suggested ones.

<!-- video: CKAN installed by the script -->
📹 _Recording: coming soon_

### 5. CKAN, one you already run

Connect to a CKAN you already have. You'll be asked for its URL and an API key;
the installer verifies both before writing anything.

<!-- video: existing CKAN -->
📹 _Recording: coming soon_

## S3 object storage

Answering yes to "Enable S3 object storage?" offers two choices:

1. **MinIO, installed alongside the Endpoint** — adds the Compose `s3` profile
   (the `pgsty/silo` image, a community fork of MinIO) and writes
   `S3_ENDPOINT=minio:9000` with the development credentials
   `minioadmin` / `minioadmin123`. Its API is published on the host as port
   9002 and its console as 9003.
2. **An S3-compatible service you already have** — asks for the endpoint
   (`host:port`, or `s3.amazonaws.com`), access key, secret key, region
   (default `us-east-1`) and whether to use https.

Either way `S3_ENABLED=True` is written, which adds the S3 Management tool to
the UI. See [minio-setup.md](minio-setup.md).

## Listed on the platform

Registration asks "List this Endpoint on the platform?" (default yes). The
answer is stored in the Federation registration, and the installer writes it
to `IS_PUBLIC`: `True` makes the Endpoint post its periodic metrics report to
the Federation (`METRICS_ENDPOINT`, which the installer sets to the Federation
it was pointed at), so it shows up as active; `False` keeps the report local.
It does not affect who can read the Endpoint's data. An Endpoint that is not
registered always gets `IS_PUBLIC=False`.

## Optional features

During registration the installer can turn on extra features. Each is off by
default; answer yes to enable it:

- **JupyterHub** — shows a JupyterHub link in the UI. Asks for the URL it should
  point to.
- **Data streaming (Kafka)** — sets `KAFKA_CONNECTION=True` and starts a Kafka
  broker alongside the Endpoint (Compose `kafka` profile).
- **Remote execution** — lets the Endpoint drive the Remote Execution API. Asks
  for that service's URL.

A URL you enter without a scheme gets `https://` added automatically.

<!-- video: enabling optional features -->
📹 _Recording: coming soon_

## After installing

- The UI is at `http://<host>:<port>/ui/` (the installer prints the exact URL).
- Sign in with your access token — copy it from your user panel on the
  platform — or with your username and password.
- As the Endpoint's administrator you'll see the management areas (datasets,
  services, organizations, access requests).

## Running it again / other options

Every prompt has a command-line flag, so the same installer works unattended.
Some useful ones:

```bash
# Reproduce a registered Endpoint without registering again
bash <(curl -fsSL https://bit.ly/ndp-ep) --config-id <id>

# See what would be written without installing anything
bash <(curl -fsSL https://bit.ly/ndp-ep) --dry-run

# Publish the Endpoint on a different port
bash <(curl -fsSL https://bit.ly/ndp-ep) --ep-api-port 8010
```

For the full list of flags and how the installer works, see
[`install/README.md`](../install/README.md). For every setting it can write,
see [configuration.md](configuration.md). For the standalone, no-catalog
install step by step — who is contacted, what is started, and the `.env` it
produces — see
[sequence-diagrams/installing-standalone-no-catalog.md](sequence-diagrams/installing-standalone-no-catalog.md).
