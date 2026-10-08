# Installing an Endpoint

```bash
git clone https://github.com/national-data-platform/ep-api.git
cd ep-api
./install/install.sh --config-id <your-federation-config-id>
```

or, without a checkout (the script clones the repository into `~/ndp-ep` —
`EP_INSTALL_DIR`, `EP_REPO_URL` and `EP_REPO_REF` override the location,
repository and branch or tag — and runs from there):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/national-data-platform/ep-api/main/install/install.sh) [options]
```

The installer needs `curl`, `python3`, `docker` and Docker Compose (`git` too
when it has to clone). It renders `.env` from `example.env`, builds the image
from the checkout and starts it with `docker compose up -d --build`, then waits
for `/health` and prints the UI address.

The configuration id comes from registering the Endpoint with the NDP
Federation. A walk-through for operators is in
[docs/installing-with-the-script.md](../docs/installing-with-the-script.md).

## Registering

Without a configuration id, an interactive run offers to register the Endpoint.
Registration (`POST /ep/simple` on the Federation) creates this Endpoint's
**Keycloak client and group**, which is what the group-based access control is
keyed on. It also fetches a staging-catalog token and registers the Endpoint in
Affinities.

It needs your NDP access token, from your user panel on the platform. The user
id the Federation records as the group's administrator is read from that
token, so it always matches whoever registered.

Registration happens **before** anything is installed: the configuration it
returns then drives the rest of the install, exactly as an id passed on the
command line would. Keep the id it prints — `--config-id <id>` reproduces the
same Endpoint without registering again.

The Federation defaults to production (`https://federation.ndp.utah.edu`),
where registering creates a real Keycloak client; the installer says so before
asking. `--env test` selects `https://federation.ndp.utah.edu/test`, and
`--federation-url` any other. The URL in use is printed at the start of every
run.

From the registration the installer sets:

| Registration field | `.env` |
|---|---|
| organization, endpoint name | `ORGANIZATION`, `EP_NAME` |
| group | `ENABLE_GROUP_BASED_ACCESS=True`, `GROUP_NAMES=<group>` |
| streaming | `KAFKA_CONNECTION=True` and the `kafka` compose profile |
| JupyterHub | `USE_JUPYTERLAB=True`, `JUPYTER_URL` |
| staging catalog URL and key | `PRE_CKAN_ENABLED=True`, `PRE_CKAN_URL`, `PRE_CKAN_API_KEY`, `PRE_CKAN_ORGANIZATION=ep-<config-id>` |
| listed on the platform | `IS_PUBLIC` |

A remote-execution URL given while registering sets `REXEC_CONNECTION=True`
and `REXEC_DEPLOYMENT_API_URL`; the Federation does not store it, so it is
applied only in the run that registers. Whatever the Federation,
`METRICS_ENDPOINT` is set to `<federation-url>/metrics/`. Without a
registration `IS_PUBLIC` is `False`, so no metrics are posted.

## Installing interactively

Run it with no arguments on a terminal and it asks, in this order (each
question is preceded by a short explanation, omitted here):

```
  Configuration id (blank to skip):

  Which local catalog should this Endpoint use?
    1) None — nothing is stored locally (quickest)
    2) MongoDB, installed alongside the Endpoint
    3) MongoDB, one I already have
    4) CKAN, installed by this script (takes several minutes)
    5) CKAN, one I already have
  Choice [1]:

  Enable S3 object storage? [y/N]:

  Register this Endpoint with the Federation now? [Y/n]:
    yes → Your NDP access token (not shown):
          Organization name [My-Organization]:
          Endpoint name [my_endpoint]:
          Contact email:
          List this Endpoint on the platform? [Y/n]:
          Enable JupyterHub? [y/N]:
          Enable data streaming (Kafka)? [y/N]:
          Enable remote execution? [y/N]:
          Continue? [Y/n]:
    no  → Organization name [My-Organization]:
          Endpoint name [my_endpoint]:

  Port to publish the Endpoint on [8002]:
  Authentication service (AAI) URL [https://idp.nationaldataplatform.org/temp/information]:
  Enable access requests? [y/N]:
```

- With a configuration id (typed, or passed with `--config-id`), the
  registration question is skipped and the installer first offers to use
  remembered settings (below).
- Catalog choices 3 and 5 ask for the existing MongoDB connection string, or
  the CKAN URL, API key and the username the key belongs to. Choice 4 asks,
  after the port, for CKAN's https, http and application ports and the
  sysadmin to create.
- Answering yes to S3 asks whether to install MinIO or use an S3-compatible
  service you already run (endpoint, keys, region, https).
- The suggested Endpoint port is the first free one from 8002 (or from
  `--ep-api-port`); the CKAN ports likewise from 8443, 81 and 5000.

Enter accepts the value in brackets. Nothing is written or started until the
answers are given; before installing CKAN there is one more confirmation.

### Without prompts

Prompts are skipped entirely when there is no terminal (CI, the sandbox) or
when `--yes` is given. Every answer then comes from a flag or its default, and
no registration is attempted, so an unattended install that should belong to
the Federation needs `--config-id`.

An existing `.env` is always copied to `.env.backup.<timestamp>` first.
Without `--yes`, the installer then asks before overwriting it.

## Access requests

The self-service workflow: someone without access asks for it from the login
screen, and an administrator approves or rejects it from the UI. Requests are
stored in MongoDB, read through `MONGODB_CONNECTION_STRING`, whatever the
catalog is — so answering yes (or `--access-requests`) also starts the bundled
MongoDB unless the catalog already provides one, and points the Endpoint at it.
Approval grants membership of the first `GROUP_NAMES` entry, which for a
registered Endpoint is the group the Federation created for it.

The `mongo-express` administration console in the compose file has its own
profile and is never started by the installer — it exposes the whole database
with the same demo credentials in every deployment. Bring it up deliberately if
you want it:

```bash
docker compose --profile mongodb --profile mongo-express up -d
```

[docs/sequence-diagrams/installing-standalone-no-catalog.md](../docs/sequence-diagrams/installing-standalone-no-catalog.md)
follows a standalone run end to end — every prompt, who is contacted, what is
started, and the `.env` it produces.

## Remembered settings

A Federation registration does not record the catalog, object storage, access
requests, the port or the AAI URL. With a configuration id, the installer
offers to keep those answers in the Federation under that same id
(`/ep/<id>/settings`), so installing the Endpoint again — here or on another
machine — reuses them. Accepting asks for your NDP access token; declining
asks for nothing and sends nothing.

Only answers travel. Credentials — the CKAN and S3 keys, the token itself — are
not remembered; `install/remembered_settings.py` lists what is.

If the Federation cannot be reached, or does not offer remembered settings,
the installer says so and carries on.

## Options

`./install/install.sh --help` prints the same list.

| Option | |
|---|---|
| `--config-id <id>` | Federation configuration id (`--config_id` is accepted too) |
| `--federation-url <url>` | default `https://federation.ndp.utah.edu` (`--federation_url` is accepted too) |
| `--env prod\|test` | pick the Federation by name; ignored when `--federation-url` is given |
| `--backend none\|mongodb\|ckan` | local catalog backend, default `none` |
| `--mongodb-url <url>` | use this existing MongoDB instead of starting one |
| `--ep-api-port <port>` | host port for the Endpoint, default `8002` |
| `--access-requests` | enable the access-request workflow |
| `--s3` | enable S3 storage with the bundled MinIO (compose profile `s3`) |
| `--s3-endpoint <host>` | use this existing S3-compatible service instead (implies `--s3`) |
| `--s3-access-key`, `--s3-secret-key` | its credentials, required with `--s3-endpoint` |
| `--s3-region <region>` | default `us-east-1` |
| `--s3-secure` | reach that S3 over https |
| `--ckan-*` | see [CKAN](#ckan) |
| `--dry-run` | render the configuration and run the checks, start nothing |
| `--no-start` | write everything, bring nothing up; prints the command to start it |
| `--yes` | no prompts at all (see [Without prompts](#without-prompts)), and overwrite an existing `.env` without asking |
| `-h`, `--help` | usage |

The underscore spellings are the ones the platform's create-endpoint page
sends; the hyphenated ones are the documented spellings.

`--dry-run` is the quickest way to see what a registration would produce. It
never installs anything, including CKAN.

### No local catalog

The default, and the quickest Endpoint to stand up:

```bash
./install/install.sh --backend none
```

Nothing is installed and nothing is stored here. The Endpoint authenticates
users, searches the platform's global catalog, serves its UI and reports to
the Federation. It renders `LOCAL_CATALOG_BACKEND=none` and
`CKAN_LOCAL_ENABLED=False`, which leaves the routes that write to a local
catalog unmounted — nothing can be published, including to the staging
catalog. Re-running the installer with `--backend mongodb` or `--backend ckan`
adds a catalog later.

`/ready` reports the local catalog as `disabled` rather than down, so an
Endpoint with no catalog is healthy rather than perpetually 503.

### MongoDB

The installer starts the bundled MongoDB (compose profile `mongodb`) and sets
`MONGODB_CONNECTION_STRING=mongodb://admin:admin123@mongodb:27017`, unless you
point at one you already run:

```bash
./install/install.sh --backend mongodb --mongodb-url mongodb://your-host:27017
```

With `--mongodb-url` the bundled MongoDB is not started. The connection string
must be reachable from inside the Endpoint container — a MongoDB on the host is
`mongodb://host.docker.internal:27017`.

### CKAN

```bash
./install/install.sh --config-id <id> --backend ckan
```

installs CKAN, waits for it to come up, creates a sysadmin and mints an API
token for the Endpoint to use. CKAN is a separate project with its own compose
stack, so it is cloned **next to** this repository (`../ndp-ckan` by default),
not into it.

| Option | |
|---|---|
| `--ckan-url`, `--ckan-api-key` | use a CKAN that already exists instead of installing one |
| `--ckan-dir <path>` | where to install it, default `../ndp-ckan` |
| `--ckan-repo <url>` | default `https://github.com/sci-ndp/pop-ckan-docker.git` |
| `--ckan-sysadmin <name>` | account to create, default `ckan_admin` |
| `--ckan-password <pass>` | its password, default generated |
| `--ckan-site-url <url>` | how the Endpoint reaches CKAN, default `https://<host-ip>:<ckan-ssl-port>` |
| `--ckan-ssl-port <port>` | CKAN's https port on the host, default `8443` |
| `--ckan-http-port <port>` | CKAN's http port on the host, default `81` |
| `--ckan-app-port <port>` | CKAN's application port on the host, default `5000` |

The minted token, the CKAN URL and the sysadmin credentials are written to
`.env.install-state` (mode 600, ignored by git). Re-running the installer
reuses them instead of minting another token, so it is safe to run repeatedly.

An installed CKAN is served over https with a self-signed certificate, so the
installer sets `CKAN_VERIFY_SSL=False` and uses `curl -k` for its checks.

Reachability and the key are checked separately, so an unreachable CKAN is not
reported as a bad key. The key is checked with `api_token_list`, which answers
403 without a valid token — most CKAN read actions answer 200 to anonymous
callers, so checking against one of those would pass with any string at all
and prove nothing. Checking the key needs a username, so with `--ckan-url`
pass `--ckan-sysadmin <name>` to enable it; without it the installer says the
key went unverified rather than implying it passed.

## How it works

**It never edits files in this repository.** The published port is set with
`EP_API_PORT`, which `docker-compose.yml` reads (`"${EP_API_PORT:-8002}:80"`),
and optional services with compose profiles.

**It has no list of settings of its own.** `.env` is rendered from
`example.env` by `install/render_env.py`, which keeps every comment and
documented default and fails if the installer sets a variable `example.env`
does not document (`install/tests/test_render_env.py` checks this too). A
variable added to `example.env` reaches new installations without this
directory changing.

Optional integrations — Kafka, S3, JupyterLab, Pelican, affinities, remote
execution, the staging catalog, identity-provider sign-in — and `IS_PUBLIC`
are switched **off** unless the answers or the registration provide them.
`example.env` is written as a demo with them on, which is right for a reference
file and wrong for a fresh install.

## Testing changes

Unit tests, run by CI along with the rest of the suite:

```bash
pytest install/tests/
```

To exercise the installer itself, a sandbox runs it inside a throwaway
Docker-in-Docker container, so every run starts from a clean machine and the
host's Docker state is untouched:

```bash
./install/tests/sandbox.sh                                   # render only
./install/tests/sandbox.sh -- --backend mongodb --yes        # full install
./install/tests/sandbox.sh -- --config-id <id> --dry-run --yes
./install/tests/sandbox.sh --keep -- --backend mongodb --yes # leave it up
./install/tests/sandbox.sh --shell                           # look around
```

The sandbox copies the working tree, not a git export, so uncommitted changes
are what gets tested.

## Not done

- **JupyterHub is not provisioned.** A registration that asks for it sets
  `USE_JUPYTERLAB` and `JUPYTER_URL` so the UI links to it; no JupyterHub is
  started.
- **Identity-provider sign-in is not offered**, and the installer leaves
  `OIDC_ENABLED=False`. The client a registration creates is confidential, so
  the browser's code exchange is refused, and its tokens carry no `sub` claim,
  which `AUTH_API_URL` looks the user up by. The installer reports the client
  id and stops there. The `OIDC_*` settings are read by the API, so a
  deployment with a working public client can switch it on by hand. See
  [docs/configuration.md](../docs/configuration.md).
