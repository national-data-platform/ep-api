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
you. Registration is what creates this Endpoint's **Keycloak client and
group**, so it is also what makes identity-provider sign-in possible without
an administrator having to set anything up by hand. It also fetches a
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

  Where should this Endpoint store its catalog?
    1) MongoDB, installed alongside the Endpoint (simplest)
    2) CKAN, installed by this script (takes several minutes)
    3) CKAN, one I already have
  Choice [1]:

  Port to publish the Endpoint on [8003]:
  Authentication service (AAI) URL [https://idp.nationaldataplatform.org/temp/information]:
  Offer sign-in through the identity provider? [y/N]:
```

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
| `--backend mongodb\|ckan` | local catalog backend, default `mongodb` |
| `--ep-api-port <port>` | host port for the API, default `8002` |
| `--dry-run` | render the configuration and run the checks, start nothing |
| `--no-start` | write everything, bring nothing up |
| `--yes` | do not prompt before overwriting an existing `.env` |

`--dry-run` is the quickest way to see what a registration would produce. It
never installs anything, including CKAN.

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
- **Identity-provider sign-in is left off**, even when the registration
  carries a `client_id`. The registration names the realm but not the
  identity provider's host, and `OIDC_ISSUER` has to agree with
  `AUTH_API_URL`; guessing one from the other would fail at the last step of a
  login, which looks like a credentials problem and is not. See
  [docs/configuration.md](../docs/configuration.md).
