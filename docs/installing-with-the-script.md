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
2. **Local catalog** — where this Endpoint stores its datasets, or whether it
   stores any at all (see below).
3. **Register with the Federation** — answer yes and give your token; this is
   what lists the Endpoint on the platform and creates its Keycloak group,
   which the group-based access control is keyed on. Answer no for a
   standalone Endpoint: it will not be listed, and it reports nothing back.
4. **Endpoint port** and **authentication service** — sensible defaults are
   offered; press Enter to accept.

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

## Optional features

During registration the installer can turn on extra features. Each is off by
default; answer yes to enable it:

- **JupyterHub** — shows a JupyterHub link in the UI. Asks for the URL it should
  point to.
- **Data streaming (Kafka)** — lets the Endpoint manage and stream Kafka topics,
  and starts a Kafka broker alongside it.
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
