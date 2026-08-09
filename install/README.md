# Installing an Endpoint

```bash
git clone https://github.com/national-data-platform/ep-api.git
cd ep-api
./install/install.sh --config-id <your-federation-config-id>
```

The configuration id comes from registering the Endpoint with the NDP
Federation. The registration supplies the organization, the access group, and
whether streaming and a staging catalog are in play; the installer applies
those on top of the documented defaults and brings the stack up.

## Registering

Without a configuration id, the installer offers to register the Endpoint for
you. Registration creates this Endpoint's **Keycloak client and group**, which
is what the group-based access control is keyed on. It also fetches a
staging-catalog token and registers the Endpoint in Affinities.

It needs your NDP access token, from your user panel on the platform. The user
id the Federation records as the group's administrator is read from that
token, so it always matches whoever registered.

Registration happens **before** anything is installed: the configuration it
returns then drives the rest of the install, exactly as an id passed on the
command line would. Registering afterwards would mean reconfiguring what had
just been built.

Keep the id it prints — `--config-id <id>` reproduces the same Endpoint
without registering again.

`--federation-url` defaults to production, where registering creates a real
Keycloak client. The installer says so before asking you to confirm.

## Installing

Run it with no arguments and it asks:

```bash
./install/install.sh
```

```
  Federation configuration id, if you have one (blank to skip):
  Organization name [My-Organization]:
  Endpoint name [my_endpoint]:

  Which local catalog should this Endpoint use?
    1) None — nothing is stored locally (quickest)
    2) MongoDB, installed alongside the Endpoint
    3) MongoDB, one I already have
    4) CKAN, installed by this script (takes several minutes)
    5) CKAN, one I already have
  Choice [1]:

  Port to publish the Endpoint on [8003]:
  Authentication service (AAI) URL [https://idp.nationaldataplatform.org/temp/information]:
  Enable access requests? [y/N]:
```

**Access requests** are the self-service workflow: someone without access asks
for it from the login screen, and an administrator approves or rejects it from
the UI. They are stored in MongoDB, read through `MONGODB_CONNECTION_STRING`,
whatever the catalog is — so answering yes installs a MongoDB unless the
catalog already provides one, and points the Endpoint at it. That is the whole
answer: nothing else has to be arranged.

A MongoDB is started on its own. The `mongo-express` administration console
that ships in the compose file has its own profile and is never started for
you — it exposes the whole database with credentials that are the same demo
pair in every deployment. Bring it up deliberately if you want it:

```bash
docker compose --profile mongodb --profile mongo-express up -d
```

[docs/sequence-diagrams/installing-standalone-no-catalog.md](../docs/sequence-diagrams/installing-standalone-no-catalog.md)
follows that run end to end — every prompt, who is contacted, what is started,
and the `.env` it produces.

Enter accepts the value in brackets. Suggested ports are picked from what is
actually free on the machine, so the defaults do not collide with whatever is
already running. Nothing is written or downloaded until the answers are
confirmed, and `--dry-run` shows the resulting configuration without touching
anything.

Every question can be answered with a flag instead, which is what makes the
same script usable unattended. Prompts are skipped entirely when there is no
terminal (CI, the sandbox) or when `--yes` is given, so automation never hangs
waiting for input.

## Options

| Option | |
|---|---|
| `--config-id <id>` | Federation configuration id |
| `--federation-url <url>` | defaults to `https://federation.ndp.utah.edu` |
| `--backend none\|mongodb\|ckan` | local catalog backend, default `none` |
| `--ep-api-port <port>` | host port for the API, default `8002` |
| `--access-requests` | enable the access-request workflow, installing MongoDB for it unless the catalog already provides one |
| `--dry-run` | render the configuration and run the checks, start nothing |
| `--no-start` | write everything, bring nothing up |
| `--yes` | do not prompt before overwriting an existing `.env` |

`--dry-run` is the quickest way to see what a registration would produce. It
never installs anything, including CKAN.

### No local catalog

The default, and the quickest Endpoint to stand up:

```bash
./install/install.sh --backend none
```

Nothing is installed and nothing is stored here. The Endpoint authenticates
users, searches the platform's global catalog, serves its UI and reports to the
Federation, which is all most Endpoints are asked to do. It renders
`LOCAL_CATALOG_BACKEND=none` and `CKAN_LOCAL_ENABLED=False`, which leaves the
routes that write to a local catalog unmounted — nothing can be published,
including to the staging catalog. Re-running the installer with `--backend
mongodb` or `--backend ckan` adds a catalog later.

`/ready` reports the local catalog as `disabled` rather than down, so an
Endpoint with no catalog is healthy rather than perpetually 503.

### MongoDB

The installer starts a MongoDB alongside the Endpoint, unless you point at one
you already run:

```bash
./install/install.sh --backend mongodb --mongodb-url mongodb://your-host:27017
```

With `--mongodb-url` the bundled MongoDB is not started; the Endpoint uses the
one you give. The connection string must be reachable from inside the Endpoint
container — a MongoDB on the host is `mongodb://host.docker.internal:27017`.

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
| `--ckan-site-url <url>` | how the Endpoint reaches CKAN, default `https://<host-ip>:8443` |

The minted token, the CKAN URL and the sysadmin credentials are written to
`.env.install-state` (mode 600, ignored by git). Re-running the installer
reuses them instead of minting another token, so it is safe to run repeatedly.

CKAN is served over https with a self-signed certificate, so the installer
sets `CKAN_VERIFY_SSL=False` and uses `curl -k` for its checks.

Reachability and the key are checked separately, so an unreachable CKAN is not
reported as a bad key. The key is checked with `api_token_list`, which answers
403 without a valid token — most CKAN read actions answer 200 to anonymous
callers, so checking against one of those would pass with any string at all
and prove nothing. Checking the key needs a username, so with `--ckan-url`
pass `--ckan-sysadmin <name>` to enable it; without it the installer says the
key went unverified rather than implying it passed.

## How it works, and why

The installer does two things deliberately, both of which come from problems
with the previous one.

**It never edits files in this repository.** The previous installer adjusted
the published port with a literal substitution:

```bash
sed -i 's|"8002:8000"|"${EP_API_PORT:-8001}:8000"|' docker-compose.yml
```

The file maps `"8002:80"`, not `"8002:8000"`. The pattern stopped matching at
some point, and because `sed -i` exits 0 when it matches nothing, the port
override silently stopped working. `docker-compose.yml` now reads
`"${EP_API_PORT:-8002}:80"`, so the port is set with an environment variable
and nothing has to rewrite the file.

**It has no list of settings of its own.** `.env` is rendered from
`example.env`, which documents every variable and its default. The previous
installer kept its own hardcoded list and had fallen eleven variables behind —
an Endpoint installed with it came up without affinities, without access
requests and without identity-provider sign-in, with nothing reporting a
problem. A variable added to `example.env` now reaches new installations
without this directory changing.

`install/tests/test_render_env.py` enforces that: it fails if the installer
sets a variable `example.env` does not document. It caught `IS_PUBLIC` — read
by the API and documented in `docs/configuration.md`, but missing from
`example.env` — the first time it ran.

Optional integrations (Kafka, S3, JupyterLab, Pelican, affinities, rexec,
identity-provider sign-in) are switched **off** unless something provides
them. `example.env` is written as a demo that shows every setting turned on,
which is right for a reference file and wrong for a fresh install.

## Testing changes

Unit tests for the rendering, run by CI along with the rest of the suite:

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

## Not done yet

- **Kafka and JupyterHub are not provisioned.** A registration that asks for
  streaming or JupyterHub configures the Endpoint for them but does not stand
  them up.
- **Identity-provider sign-in is not offered**, and the installer no longer
  asks about it. There is no client an Endpoint can sign in through: the ones
  a registration creates are confidential, so the browser's code exchange is
  refused with "Invalid client or Invalid client credentials", and their
  tokens carry no `sub` claim — which `AUTH_API_URL` looks the user up by, so
  it answers 500 even once the exchange succeeds. The scope that supplies
  `sub` is not assignable from this side. Until that is settled with whoever
  administers the identity provider, offering the option could only produce a
  button that fails after a successful login. The `OIDC_*` settings remain
  documented and are read by the API, so a deployment with a working client
  can switch it on by hand. See
  [docs/configuration.md](../docs/configuration.md).
