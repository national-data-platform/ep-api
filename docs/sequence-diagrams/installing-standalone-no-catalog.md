# Installing a standalone Endpoint with no catalog

The lightest install there is, and the one to start from:

- **no Federation registration** — the Endpoint is not listed on the platform,
- **no local catalog** — no MongoDB, no CKAN, nothing stored here,
- **every other answer left at its default**.

```bash
./install/install.sh
```

Answer the prompts by pressing Enter, except *Register this Endpoint with the
Federation now?*, which is answered `n` (its default is yes).

The unattended equivalent is:

```bash
./install/install.sh --backend none --yes
```

With `--yes` no prompt is shown at all, so organization and name are not
asked: `.env` keeps `example.env`'s demo values `ORGANIZATION-DEMO` and
`EP-DEMO`, and no `AUTH_API_URL` override is written (`example.env`'s value
is the same NDP AAI URL). That run sets 15 values instead of 18; everything
else below is the same.

## The sequence

```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant Installer as install.sh
    participant Render as render_env.py
    participant Docker as Docker Compose
    participant EP as Endpoint container
    participant AAI as Authentication service
    participant Fed as NDP Federation

    Operator->>Installer: ./install/install.sh

    rect rgb(245, 245, 245)
    Note over Installer: Checking prerequisites
    Installer->>Docker: docker info, compose version
    Docker-->>Installer: available
    Note over Installer: curl, python3 and example.env must be present
    end

    rect rgb(245, 245, 245)
    Note over Operator,Installer: Asking — nothing is written yet
    Installer->>Operator: Configuration id? (blank to skip)
    Operator-->>Installer: (blank)
    Installer->>Operator: Which local catalog? [1] None
    Operator-->>Installer: (Enter)
    Installer->>Operator: Enable S3 object storage? [y/N]
    Operator-->>Installer: (Enter)
    Installer->>Operator: Register this Endpoint with the Federation now? [Y/n]
    Operator-->>Installer: n
    Installer->>Operator: Organization name? [My-Organization]
    Operator-->>Installer: (Enter)
    Installer->>Operator: Endpoint name? [my_endpoint]
    Operator-->>Installer: (Enter)
    Installer->>Operator: Port to publish on? [8002, or the first free one after it]
    Operator-->>Installer: (Enter)
    Installer->>Operator: Authentication service (AAI) URL? [NDP AAI]
    Operator-->>Installer: (Enter)
    Installer->>Operator: Enable access requests? [y/N]
    Operator-->>Installer: (Enter)
    end

    Note over Installer,Fed: No configuration id and no registration:<br/>the Federation is never contacted

    rect rgb(245, 245, 245)
    Note over Installer: Integrations off: IS_PUBLIC, KAFKA_CONNECTION,<br/>USE_JUPYTERLAB, S3_ENABLED, PELICAN_ENABLED,<br/>AFFINITIES_ENABLED, REXEC_CONNECTION,<br/>PRE_CKAN_ENABLED, OIDC_ENABLED = False
    Note over Installer: METRICS_ENDPOINT = <federation-url>/metrics/
    Note over Installer: Selecting the local catalog backend:<br/>LOCAL_CATALOG_BACKEND=none, CKAN_LOCAL_ENABLED=False,<br/>CKAN and MongoDB settings blanked, no compose profile added
    end

    alt A .env already exists
        Installer->>Installer: copy it to .env.backup.<timestamp>
        Installer->>Operator: overwrite?
        Operator-->>Installer: y
    end

    Installer->>Render: example.env + the answers
    Render-->>Installer: .env (18 values set)
    Note over Render: Every variable comes from example.env,<br/>so nothing new is missed

    Installer->>AAI: POST with an invalid token
    AAI-->>Installer: 400 — reachable, as expected
    Note over Installer,AAI: Read back from the rendered file,<br/>so a mistake surfaces here and not at runtime

    Installer->>Docker: EP_API_PORT=8002 docker compose up -d --build
    Docker->>EP: build the image from the checkout,<br/>start ndp-ep-api (API + UI, no other container)
    EP-->>Docker: running

    loop up to 30 times, every 2s
        Installer->>EP: GET /health
    end
    EP-->>Installer: 200 healthy
    Installer->>Operator: Installed. UI: http://localhost:8002/ui/

    rect rgb(245, 245, 245)
    Note over EP,Fed: From here on, on its own
    Note over EP: One worker (the leader) collects metrics<br/>at startup and every 3300s and logs them
    Note over EP,Fed: Nothing is posted: IS_PUBLIC is False without a<br/>registration, and posting is gated on it
    end
```

## The `.env` it produces

`.env` is rendered from `example.env`, so it keeps every comment and every
variable the Endpoint documents. Stripped of comments, this is the whole file
(the output of `--dry-run` with the answers above):

```ini
ROOT_PATH=
ORGANIZATION=My-Organization
EP_NAME=my_endpoint
IS_PUBLIC=False
METRICS_INTERVAL_SECONDS=3300
METRICS_ENDPOINT=https://federation.ndp.utah.edu/metrics/
NETBIRD_ENABLED=False
NETBIRD_IP=
NETBIRD_GROUP=
ENABLE_GROUP_BASED_ACCESS=False
GROUP_NAMES=
ENABLE_ACCESS_REQUESTS=False
ACCESS_REQUESTS_COLLECTION=access_requests
LOCAL_CATALOG_BACKEND=none
CKAN_LOCAL_ENABLED=False
CKAN_URL=
CKAN_API_KEY=
CKAN_VERIFY_SSL=True
MONGODB_CONNECTION_STRING=
MONGODB_DATABASE=ndp_local_catalog
PRE_CKAN_ENABLED=False
PRE_CKAN_URL=
PRE_CKAN_API_KEY=
PRE_CKAN_VERIFY_SSL=True
PRE_CKAN_ORGANIZATION=
KAFKA_CONNECTION=False
KAFKA_HOST=kafka
KAFKA_PORT=9093
MAX_STREAMS=10
TEST_TOKEN=testing_token
AUTH_API_URL=https://idp.nationaldataplatform.org/temp/information
OIDC_ENABLED=False
USE_JUPYTERLAB=False
JUPYTER_URL=http://jupyterlab:8888
S3_ENABLED=False
S3_ENDPOINT=minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_SECURE=False
S3_REGION=us-east-1
PELICAN_ENABLED=False
PELICAN_FEDERATION_URL=
PELICAN_DIRECT_READS=False
PELICAN_MAX_READ_BYTES=10485760
PELICAN_EVENT_SERVER_URL=
PELICAN_EVENT_CLIENT_ID=
PELICAN_EVENT_USERNAME=
PELICAN_EVENT_PASSWORD=
PELICAN_EVENT_VIRTUAL_HOST=playground
PELICAN_EVENT_HEARTBEAT_MS=10000
REXEC_CONNECTION=False
REXEC_DEPLOYMENT_API_URL=
AFFINITIES_ENABLED=False
AFFINITIES_URL=
AFFINITIES_EP_UUID=
AFFINITIES_TIMEOUT=30
```

The 18 values the installer set:

| Variable | Value | Why |
|---|---|---|
| `ORGANIZATION`, `EP_NAME` | `My-Organization`, `my_endpoint` | The answers given at the prompt |
| `AUTH_API_URL` | NDP AAI | The answer given at the prompt: where login tokens are validated |
| `METRICS_ENDPOINT` | `<federation-url>/metrics/` | Written on every install for the Federation the run was pointed at (production by default) |
| `LOCAL_CATALOG_BACKEND` | `none` | No local catalog |
| `CKAN_LOCAL_ENABLED` | `False` | Leaves the routes that write to a local catalog unmounted |
| `CKAN_URL`, `CKAN_API_KEY`, `MONGODB_CONNECTION_STRING` | empty | Nothing must point at a service that was not installed |
| `IS_PUBLIC` | `False` | No registration, so nothing is reported to the Federation |
| `KAFKA_CONNECTION`, `S3_ENABLED`, `USE_JUPYTERLAB`, `PELICAN_ENABLED`, `AFFINITIES_ENABLED`, `REXEC_CONNECTION`, `PRE_CKAN_ENABLED`, `OIDC_ENABLED` | `False` | `example.env` is a demo with several integrations on; a fresh install provisions none of them |

Everything else is `example.env`'s documented default, untouched. One of those
defaults is worth knowing: **`TEST_TOKEN=testing_token`** is a development
convenience that is accepted as a token with the `ndp_admin` role. Change it,
or clear it, on anything reachable by others.

The port is not in `.env`: it is passed to Docker Compose as `EP_API_PORT`
when the stack is started.

`METRICS_ENDPOINT` names the Federation, but nothing is sent to it: posting is
gated on `IS_PUBLIC`, which only a registration turns on.

## What this Endpoint does, and does not

**It does**: authenticate users against the NDP AAI, search the platform's
global catalog, serve its UI at `/ui/`, answer `/health` and `/ready` and
proxy to services.

`/ready` reports the local catalog as `disabled`, not as down:

```json
{"status": "healthy",
 "timestamp": "2026-10-08T12:00:00.000000Z",
 "checks": {"local_catalog": {"status": "disabled", "backend": "none"},
            "pre_ckan": {"status": "disabled"},
            "minio": {"status": "disabled"},
            "kafka": {"status": "disabled"},
            "affinities": {"status": "disabled"}}}
```

`affinities` is reported but does not count towards the verdict.

**It does not**: store anything, or tell anyone about itself. The registration,
update, delete and resource routes are not mounted at all — they are absent
from `/docs` rather than failing when called — and `/search?server=local`
answers `400 Local CKAN is disabled and cannot be used`. Publishing to the
staging catalog is off too, since it travels through the same routes. Nothing
is posted to the Federation: the Endpoint never registered, so it is not
public, and metrics stay local to its logs.

Group-based access is off (`ENABLE_GROUP_BASED_ACCESS=False`), so any user the
AAI accepts can enter; writing still needs a writer role, which on this
Endpoint can only come from a platform-wide role (`ndp_writer`, `ndp_editor`
or `ndp_admin`), because no Endpoint group is configured.
