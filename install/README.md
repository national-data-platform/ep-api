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

To try an Endpoint without registering one:

```bash
./install/install.sh --backend mongodb
```

## Options

| Option | |
|---|---|
| `--config-id <id>` | Federation configuration id |
| `--federation-url <url>` | defaults to `https://federation.ndp.utah.edu` |
| `--backend mongodb\|ckan` | local catalog backend, default `mongodb` |
| `--ckan-url`, `--ckan-api-key` | required with `--backend ckan` |
| `--ep-api-port <port>` | host port for the API, default `8002` |
| `--dry-run` | render the configuration and run the checks, start nothing |
| `--no-start` | write everything, bring nothing up |
| `--yes` | do not prompt before overwriting an existing `.env` |

`--dry-run` is the quickest way to see what a registration would produce.

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

- **CKAN is not provisioned.** `--backend ckan` connects to a CKAN that
  already exists and verifies the API key before writing anything. Installing
  CKAN and minting its token — which the previous installer did with
  `ckan user token add` — has not been brought over.
- **Kafka and JupyterHub are not provisioned.** A registration that asks for
  streaming or JupyterHub configures the Endpoint for them but does not stand
  them up.
- **Identity-provider sign-in is left off**, even when the registration
  carries a `client_id`. The registration names the realm but not the
  identity provider's host, and `OIDC_ISSUER` has to agree with
  `AUTH_API_URL`; guessing one from the other would fail at the last step of a
  login, which looks like a credentials problem and is not. See
  [docs/configuration.md](../docs/configuration.md).
