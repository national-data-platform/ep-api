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
- **HTTPS** if you plan to enable identity-provider sign-in — browsers only
  expose the crypto that flow needs over a secure connection (`localhost`
  counts, so an SSH tunnel works for testing).

## What the installer asks

Run it and answer the prompts. Each has a short explanation on screen; the main
choices are:

1. **Configuration id** — leave blank the first time and it offers to register.
2. **Local catalog** — where this Endpoint stores its datasets (see below).
3. **Register with the Federation** — answer yes and give your token; this also
   creates the Endpoint's Keycloak client and group, which is what makes
   identity-provider sign-in possible.
4. **Endpoint port**, **authentication service**, **identity-provider sign-in**
   — sensible defaults are offered; press Enter to accept.

When it finishes you'll see `Endpoint healthy` and a URL like
`http://localhost:8002/ui/`.

Keep the configuration id it prints — re-running with `--config-id <id>`
reproduces the same Endpoint without registering again.

## Catalog options

The installer offers four ways to provide the local catalog. Pick one at the
"Which local catalog should this Endpoint use?" prompt.

### 1. MongoDB, installed by the script

The simplest option. The installer starts a MongoDB alongside the Endpoint — no
external services, nothing to prepare.

<!-- video: MongoDB installed by the script -->
📹 _Recording: coming soon_

### 2. MongoDB, one you already run

Point the Endpoint at an existing MongoDB instead of starting one. You'll be
asked for a connection string reachable from inside the Endpoint container (a
MongoDB on the host is `mongodb://host.docker.internal:27017`).

<!-- video: existing MongoDB -->
📹 _Recording: coming soon_

### 3. CKAN, installed by the script

The fullest option. The installer clones CKAN, builds and starts it, creates a
sysadmin and mints an API token for the Endpoint. This takes several minutes the
first time (CKAN, Solr and Postgres). Ports that clash with other services are
avoided automatically — press Enter to accept the suggested ones.

<!-- video: CKAN installed by the script -->
📹 _Recording: coming soon_

### 4. CKAN, one you already run

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
- Sign in with your access token, your username and password, or — if you
  enabled it — the identity provider.
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
see [configuration.md](configuration.md).
