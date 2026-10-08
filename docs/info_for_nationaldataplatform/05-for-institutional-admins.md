# For institutional admins

An **NDP Endpoint** lets an institution publish its own data into the National
Data Platform under its own name and policies, while reusing NDP's shared
identity and Federation. This page is for the IT, dev-ops or data team that
installs and runs the Endpoint on behalf of the institution.

## Should we run an Endpoint?

Run one if **any** of these applies:

- Your institution wants its datasets and services to appear in NDP under its
  own name, with its own organizations and curators.
- You need a place where institution members can register data through a
  web UI and a Python library, and send it to the platform for review.
- You want object storage (S3-compatible) managed next to the catalog, so
  large data products live next to their metadata.
- You want Kafka streams to be described and discoverable.

If none of the above applies and your users only **consume** data, you do not
need an Endpoint — they can use the central NDP directly.

## The platform / institution split

| The platform provides | You provide |
|---|---|
| **Identity**: NDP accounts, groups and roles, and the authentication service every request is checked against | A **Linux host** with Docker and Docker Compose, `curl`, `python3` and `git` |
| **The NDP Federation**: registers the Endpoint, creates its access group and its staging-catalog token, lists it on the platform | Optionally, a **local catalog**: MongoDB or CKAN, installed by the installer or one you already run |
| **The global catalog** the Endpoint searches, and the **staging catalog** (Pre-CKAN) its writers send datasets to | Optionally, **S3 storage**: MinIO installed by the installer, or an S3-compatible service you already run |
| | The people who administer the Endpoint and its content policies |

Nothing is handed over by hand: there is no Endpoint UUID, CKAN token or
configuration file to receive from the NDP team. The installer obtains what it
needs from the Federation.

## How to obtain an Endpoint

1. **Get an NDP account** at
   [nationaldataplatform.org](https://nationaldataplatform.org/). Its access
   token, from the user section of the platform, is what registers the
   Endpoint.
2. **Run the installer on your host.** From the web (it clones the repository
   into `~/ndp-ep` and runs from there):

   ```bash
   bash <(curl -fsSL https://raw.githubusercontent.com/national-data-platform/ep-api/main/install/install.sh)
   ```

   or `./install/install.sh` from a checkout of
   [github.com/national-data-platform/ep-api](https://github.com/national-data-platform/ep-api).
3. **Register it**, in one of two ways:
   - **Let the installer register it.** Leave the configuration id blank and
     answer yes to *Register this Endpoint with the Federation now?*. The
     installer asks for your NDP access token, the organization, the
     Endpoint's name, a contact email, whether to list it on the platform,
     and the optional JupyterHub, streaming and remote-execution features,
     then registers it (`POST /ep/simple`). Keep the configuration id it
     prints.
   - **Register on the platform first.** The platform's create-endpoint page
     gives you an installer command with `--config-id <id>`; run that.

   Answer no to registering, with no configuration id, for a **standalone**
   Endpoint: not listed on the platform, no access group, no staging catalog.
   `--env test` or `--federation-url <url>` point the installer at a
   Federation other than production.
4. **Answer the remaining questions.** The installer asks which local catalog
   to use (none, the default; MongoDB installed alongside or one you have;
   CKAN installed by the script or one you have), whether to enable S3
   (MinIO installed alongside, or an existing S3 service), the port to
   publish the Endpoint on, the authentication service URL (the NDP one by
   default), and whether to enable access requests. Every question has a
   command-line flag for unattended runs; see `install/README.md` in the
   repository.

The installer then:

- renders `.env` from the documented `example.env`, applying the answers and
  the registration: the Endpoint's group (`GROUP_NAMES`, which gates who may
  enter), the staging-catalog URL, token and organization (`PRE_CKAN_*`),
  whether it is listed (`IS_PUBLIC`), and where to send metrics
  (`METRICS_ENDPOINT`);
- picks the Docker Compose profiles that match (`mongodb`, `s3`, `kafka`);
- installs CKAN as a separate project next to the repository (`../ndp-ckan`)
  and mints its API key, when CKAN was chosen;
- checks the authentication service, the CKAN key and the staging-catalog
  organization before starting anything;
- builds the Endpoint image from the checkout, starts the stack
  (`docker compose up -d --build`) and waits for `/health`.

`--dry-run` shows the resulting configuration without writing or starting
anything. The UI is then at `http://<host>:<port>/ui/`, and the API at
`http://<host>:<port>/`. Putting it behind your institution's domain and TLS
is up to you; `ROOT_PATH` serves it under a path prefix if needed.

## Administrators of the Endpoint

The Endpoint treats as **admin** anyone holding the per-Endpoint role
`group:<endpoint group>:admin` or the platform-wide `ndp_admin` role; admins
see the Dashboard and, with access requests enabled, the Access Requests page.
The registration makes the registering operator the administrator of the
Endpoint's group in the identity provider (Federation side; see its
documentation). A token issued before the registration does not carry the new
group: sign in with a fresh one.

With access requests enabled, users who are refused entry can ask for access,
and an admin approves them from the UI; since 0.34.46 approval adds them to
the Endpoint's group and, for writer or admin, assigns the role on it. See
[Requesting access and the role tiers](02-requesting-access-and-roles.md).

## What runs day to day

- The Endpoint serves the **web app** at `/ui/` and the **HTTP API** at `/`
  from one container (`ndp-ep-api`), plus whatever the chosen profiles add
  (MongoDB, MinIO, Kafka).
- It validates user tokens against the authentication service on every
  request.
- **Only when it is listed on the platform** (`IS_PUBLIC=True`, from *List
  this Endpoint on the platform?*), it sends a metrics report to the
  Federation at startup and every 55 minutes. The report carries the
  organization and Endpoint name, the Endpoint version, the host's **public
  IP**, CPU, memory and disk use, dataset and service counts and service
  titles, the local **CKAN URL**, which integrations are on (S3, Kafka,
  JupyterLab, staging catalog) with the Kafka host and port and the
  JupyterLab URL when they are, NetBird values when set, and whether a CKAN
  key is configured (never the key). No user tokens and no dataset content
  are sent. A report that fails is **not retried**; the next one comes an
  interval later. Details:
  [federation-and-metrics.md](../architecture/federation-and-metrics.md).

## Optional integrations

- **JupyterHub link** — from the registration; shows a link in the UI.
- **Streaming (Kafka)** — from the registration; adds the `kafka` compose
  profile and, on an Endpoint with a local catalog, lets writers register
  Kafka topics.
- **Remote execution** — from the registration run; the URL asked then is
  written to `.env`, and a later `--config-id` run does not restore it.
- **Pelican** — browse and read from Pelican federations; the installer
  leaves it off (`PELICAN_ENABLED=False`), and it is switched on in `.env`.
- **NetBird** — `NETBIRD_ENABLED`, `NETBIRD_IP` and `NETBIRD_GROUP` are only
  reported in the metrics; the Endpoint does not set up NetBird itself.

## Operational notes

- **Upgrades.** Re-run the installer: from the web it first moves `~/ndp-ep`
  to the latest `main`; from a checkout, update the checkout and run
  `./install/install.sh` again (with `--config-id <id>` for a registered
  Endpoint). It backs up the existing `.env` to `.env.backup.<timestamp>`,
  renders a new one and rebuilds the image. `docker compose pull` does **not**
  update the Endpoint: the `api` service has no published image and is built
  locally.
- **The port** is not stored in `.env`; it is passed to Docker Compose as
  `EP_API_PORT`. When starting the stack by hand, set it again
  (`EP_API_PORT=<port> docker compose --profile <profile> ... up -d --build`;
  `--no-start` prints the exact command).
- **Secrets.** `.env` holds the CKAN API key, the staging-catalog token, the
  S3 keys and `TEST_TOKEN`. `.env.install-state` holds the CKAN sysadmin
  name, password and API key the installer created. There is no encryption
  key setting. Change or clear `TEST_TOKEN` (default `testing_token`, which
  is accepted as an `ndp_admin` token) on any Endpoint others can reach.
- **Backups.** Back up `.env`, `.env.install-state`, the MongoDB volume
  (`mongodb_data`, which also holds access requests), the MinIO volume
  (`minio_data`) and, with an installed CKAN, that project's own volumes.
  The Endpoint container itself holds no data that needs backing up.
- **Privacy.** See the metrics contents above; nothing else is sent to the
  Federation after installation.

## Where to start

The Endpoint repository contains the installer, the Compose definition and
the configuration reference:
<https://github.com/national-data-platform/ep-api>. `install/README.md` lists
every installer option, and `docs/configuration.md` every setting.
