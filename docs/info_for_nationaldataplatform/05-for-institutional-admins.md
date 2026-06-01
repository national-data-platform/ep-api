# For institutional admins

An **NDP Endpoint** lets an institution publish its own data into the National
Data Platform under its own brand and policies, while reusing NDP's shared
identity and federation. This page is for the IT, dev-ops or data team that
runs the Endpoint on behalf of the institution.

## Should we run an Endpoint?

Run one if **any** of these applies:

- Your institution wants its datasets and services to appear in NDP under its
  own name, with its own organizations and curators.
- You need a place where institution members can publish data through a
  familiar web UI and a Python library, without writing to a shared central
  catalog.
- You want object-storage management (S3-compatible) integrated with the
  catalog so large data products live next to their metadata.
- You want a Kafka-based stream of data to be discoverable from NDP.

If none of the above applies and your users only **consume** data, you do not
need an Endpoint — they can use the central NDP directly.

## The platform / institution split

| The platform provides | You provide |
|---|---|
| **Identity** (AAI, CI Logon, role tiers) | The host (single Linux machine with Docker) |
| **Affinities** registration (your Endpoint's `EP_UUID`) | A **catalog database** (MongoDB or an existing CKAN) |
| **Federation** registration & periodic discovery | **Object storage** (MinIO or an existing S3) — optional |
| The `nationaldataplatform.org` shared experience | The institution's **branding** and content policies |

In practice, the NDP team gives you what you need from their side as part of
**onboarding**; you do not have to provision identity or federation from
scratch.

## How to obtain an Endpoint

1. **Get an institutional NDP account** (CI Logon, institutional email — see
   the central [Registration and Login](https://nationaldataplatform.org/documentation/registration/)
   docs).
2. **Contact the NDP team** to start the onboarding for your institution.
   The team registers your Endpoint in the federation and gives you back:
   - the Endpoint's **`EP_UUID`** in Affinities,
   - access credentials for the shared catalogs your Endpoint will need to
     talk to (CKAN and / or Pre-CKAN admin tokens),
   - the AAI configuration values (`AUTH_API_URL`, etc.) that the Endpoint
     should call.
3. **Install the Endpoint on your host**. The source and the install
   instructions live at
   [github.com/national-data-platform/ep-api](https://github.com/national-data-platform/ep-api).
   The Endpoint ships as a single Docker image (API + web UI). Depending on
   your needs, you also bring up a catalog database (MongoDB or CKAN) and
   optionally S3-compatible storage; the project's Docker Compose file uses
   **profiles** so you can opt-in piece by piece.
4. **Provide `.env` values.** Every configuration variable is documented in the
   project's `docs/configuration.md`, including which ones are required, what
   each one is for, and where to get the value.
5. **Bootstrap the first administrator.** Once the Endpoint is running, the
   first admin needs the `ndp_admin` role assigned in AAI — typically handled
   by the NDP team during onboarding. After that, the admin grants roles to
   other users through the Endpoint's **Access Requests** page.

## What runs day to day

- The Endpoint serves the **web app** and **HTTP API** at `…/ep-api/`.
- It validates user tokens against AAI on every request.
- Every ~55 minutes it sends a small **metrics payload** to the federation —
  identity, EP version, host load (CPU/memory/disk), catalog activity
  (`num_datasets`, `num_services`, service titles), and infrastructure flags
  (S3 / Kafka / JupyterLab / Pre-CKAN enabled). **No tokens, user data or
  dataset content** are sent. The Endpoint is non-blocking on this: if the
  federation is unreachable, the Endpoint keeps working and retries.

## Optional integrations

- **JupyterLab** — surface a JupyterLab link in the Endpoint UI.
- **Kafka** — register and stream-publish Kafka topics as system datasets.
- **Pelican federation** — browse / download from external Pelican federations
  (OSDF, etc.).
- **NetBird** ([netbird.io](https://netbird.io)) — when the Endpoint and its
  backends run on different machines, run a NetBird mesh VPN so they talk over
  a private encrypted overlay without exposing public ports.

## Operational notes

- **Secrets.** Tokens (CKAN, Pre-CKAN, S3) and the store encryption key live in
  the host's `.env`. Back them up; rotate them through the AAI team if they are
  ever exposed.
- **Backups.** Back up the catalog database (MongoDB or CKAN) on your normal
  institutional schedule. The Endpoint itself is stateless.
- **Updates.** New Endpoint releases are published on Docker Hub. Upgrades are
  a `docker compose pull && docker compose up -d` once your `.env` and version
  pinning are in place.
- **Privacy.** Only metadata (titles, descriptions, counts) and infrastructure
  flags are sent to the federation. Dataset content stays on the institution's
  own storage.

## Where to start

The single most useful link for an admin is the Endpoint repository — it
contains the Docker image, the Compose definition, the configuration reference
and a step-by-step demo presentation: <https://github.com/national-data-platform/ep-api>.
