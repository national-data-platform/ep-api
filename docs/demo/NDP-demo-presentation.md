---
marp: true
title: NDP — From zero to a federated, secure dataset
author: Raul Bardaji
paginate: true
theme: default
class: lead
---

<!--
 PRESENTATION + SELF-GUIDED TUTORIAL — National Data Platform (NDP)
 Audience: end users and administrators (not developers).
 Focus: WHAT you can do and HOW it looks.
 Render:  marp NDP-presentacion.md -o NDP-presentacion.pdf   (or .pptx, .html)
 [📸 ...] blocks mark where to drop a screenshot (folder ./capturas).
 Lines after "<!-- note: ... -->" are speaker notes for whoever presents.
-->

<style>
/* Brand header/footer copied from "ndp ep - presentation.pptx":
   - header: National Data Platform logo (top-left)
   - footer: partner logos band (SDSC . SCI . EarthScope . UCSD . Utah . CU Boulder)
   Applied to every slide as layered section backgrounds so content sits between
   the two bands (padding keeps text clear of them). */
section {
  padding: 96px 48px 80px 48px;
  background-image:
    url('assets/header-logo.png'),
    url('assets/footer-left.png'),
    url('assets/footer-right.png');
  background-repeat: no-repeat, no-repeat, no-repeat;
  background-position:
    left 32px top 22px,
    left 24px bottom 14px,
    right 24px bottom 14px;
  background-size:
    auto 58px,
    auto 44px,
    auto 44px;
}
/* full-slide screenshot slides: center the image */
section.imgslide { text-align: center; }
</style>

# National Data Platform (NDP)
## From zero to a federated, secure dataset

A guided demo of every component and how they work together

<!-- note: introduce in one sentence. "Today we see NDP end to end: install it,
use it from the web and from code, federate it, and connect it securely." -->

---

## What is NDP?

A platform to **publish, discover and share data** across institutions.

- Each institution runs its own **Endpoint (EP)**: its data catalog.
- EPs are **federated**: discovered and shared through a central registry.
- All with shared **identity and permissions** and, optionally, over a
  **secure private network**.

> Key idea: **distributed data, unified discovery.**

<!-- note: avoid jargon; the message is federation + access governance. -->

---

## Platform components

| Piece | What it is for | How it looks |
|---|---|---|
| <img src="assets/icons/aai.svg" height="34"/> **AAI** (Keycloak) | Who you are (login, users) | Login screen |
| <img src="assets/icons/affinities.svg" height="34"/> **Affinities** | Relationships between datasets, services and endpoints | Relationships web app |
| <img src="assets/icons/ndp-ep.svg" height="34"/> **NDP-EP** | Your catalog: datasets, resources, storage | Endpoint web app |
| <img src="assets/icons/federation.svg" height="34"/> **Federation** | Central registry of all EPs | Federation web app |
| <img src="assets/icons/python-lib.svg" height="34"/> **Python library** | Do the same from code / automate | Notebook / script |
| <img src="assets/icons/netbird.svg" height="34"/> **NetBird** (bonus) | Secure private network between machines | Network dashboard |

---

## Component interactions

![w:1080](assets/diagrams/component-interactions.svg)

<!-- note: narrate the diagram: the user signs in through AAI, which also
carries their ROLE (roles live in AAI/Keycloak, NOT in Affinities). With that
token they publish and search in the NDP-EP, backed by CKAN and S3. The EP then
registers its datasets/services in Affinities (a non-blocking relationship
registry) and reports to Federation. All of it can run over a private NetBird
network (final bonus). Derived from the C4 view in ../ep-diagrams. -->

---

## Component interactions — step by step

1. **Sign in** — the user authenticates through **AAI** (Keycloak), which also carries their **role** (viewer / writer / admin).
2. **Use the Endpoint** — with that token they publish and search in the **NDP-EP**, backed by **CKAN** (catalog) and **MinIO / S3** (storage).
3. **Register relationships** — the EP registers its datasets and services in **Affinities**, a non-blocking graph of how data, services and endpoints relate.
4. **Federate** — the EP reports to **Federation** (central registry + health & metrics).
5. **Secure transport** — all of it can run over a private, encrypted **NetBird** network.

<!-- note: roles live in AAI, NOT in Affinities. Affinities is a relationship
registry the EP writes into; it is non-blocking (the EP works even if it is down). -->

---

## Overview

> A new user is granted access, publishes a dataset, performs the same tasks from
> code, and the dataset becomes discoverable across the federation — all securely.

**Steps:**
1. Installation
2. Identity and permissions (sign in and get a role)
3. The Endpoint in action (publish and search from the web)
4. Automate with the Python library
5. Federation (the data is discovered elsewhere)
6. 🔒 Bonus: secure network with NetBird

---

# Step 1 — Installation

---

## Two ways to install

**🟢 Most users — the NDP-EP only**
Run your own **Endpoint** and connect it to the **National Data Platform**, which
already provides identity (**AAI**), **Affinities** and **Federation**.
→ install **one** component.

**🧪 Full stack — development / testing**
Run all components locally, with no dependency on the central NDP.
→ install **all** components.

> The common case is covered first; the full stack follows.

---

## Before you install — prerequisites

Have these ready; the installer writes them into `.env`:

- **AAI endpoint** — the AAI `…/information` URL, so logins and roles work.
- **Catalog backend** — a MongoDB (Compose can start it) **or** a reachable **CKAN** instance with an admin **API token**.
- **EP_UUID** — required only when using Affinities or per-EP roles (`group:<EP_UUID>:…`). It is the Endpoint's `uid` in Affinities, used as `AFFINITIES_EP_UUID`. → see appendix *Obtaining the EP_UUID*.
- **Object storage** — optional, only for S3 features.

> In the common case, the platform operators provide the AAI endpoint and, if
> applicable, the `EP_UUID`.

---

## Install the NDP-EP (the common case)

> ⚠️ **For system administrators.** Installation involves Docker, networking and
> environment configuration — it should be done by someone with sysadmin skills.

```bash
git clone https://github.com/national-data-platform/ep-api.git
cd ep-api
cp example.env .env      # configure your deployment
docker compose up -d     # the Endpoint only
```

> The CKAN backend requires an existing, reachable CKAN instance and an administrator API token (`CKAN_API_KEY`). The MongoDB backend has no such prerequisite.

> Run only the Endpoint, or add local backends with **Compose profiles** (next slide).

> 📖 `.env` variables are explained in **`docs/configuration.md`** (template: `example.env`).

---

## Compose profiles — core backends

`docker compose --profile <name> up -d` — combine as many as you need:

| Profile | What it starts |
|---|---|
| *(none)* | **NDP-EP only** (API + web UI) |
| `mongodb` | MongoDB + Mongo Express (local catalog DB) |
| `s3` | MinIO (S3-compatible object storage) |
| `kafka` | Kafka + Zookeeper + Kafka UI (streaming) |

---

## Compose profiles — extras

| Profile | What it starts |
|---|---|
| `jupyter` | JupyterLab |
| `pelican` | Pelican federation (registry, director, origin, cache) |
| `full` | All backends above |

<!-- note: profiles let an admin run only the EP (connecting to the platform's
shared services) or spin up local backends for development/testing. -->

---

## What you operate vs. what the platform provides

| 🛠️ You operate (your Endpoint) | ☁️ Shared by the platform |
|---|---|
| **NDP-EP** — API + web UI | **AAI** — identity & roles |
| **Catalog database** — CKAN or MongoDB | **Affinities** — relationship registry |
| **Object storage** — MinIO / S3 *(optional)* | **Federation** — registry & discovery |


<!-- note: this is the responsibility boundary. In the common case you only run
the EP + its data backends; identity/affinities/federation are the platform's. -->

---

# Full stack (development / testing)
### Only if you want the whole system locally

<!-- note: this whole sub-section is the dev/test path. Most users skip it and
just run the NDP-EP from the previous slide. -->

---

## Startup order (full stack)

```
1) AAI (Keycloak)      → identity first, everything depends on it
2) Affinities          → relationships (data · services · endpoints)
3) Federation          → central registry
4) NDP-EP (+ backends)  → catalog, connects to AAI and Federation
        backends: CKAN · MongoDB · MinIO (S3 storage)
```

Each component starts the same way: enter its folder and `docker compose up -d`.

<!-- note: stress: same gesture in each repo; order matters due to dependencies. -->

---

## 1) Start AAI (identity)

```bash
git clone https://github.com/sci-ndp/ndp-keycloak-aai-old.git
cd ndp-keycloak-aai-old
cp .env_template .env        # set admin user/password + domain
# place fullchain.pem & privkey.pem in SSL/certificates/  (TLS)
docker compose up -d --build
```

**What you will see:** the Keycloak admin console and the NDP login screen.

<!-- 📸 screenshots/10-keycloak-login.png — NDP "Welcome back" login screen -->
<!-- 📸 screenshots/11-keycloak-admin.png — Keycloak admin console (realm NDP) -->

---

## 2) Start Affinities (relationship registry)

```bash
git clone https://github.com/sci-ndp/ndp-affinities.git
cd ndp-affinities
cp .env.example .env         # optional: customize DB user/password
docker compose up -d
```

**What you will see (default URLs):**
- API: `http://localhost:8000/docs`
- **Affinities web app**: `http://localhost:3000`
- Database admin (pgAdmin): `http://localhost:5050`

<!-- 📸 screenshots/12-affinities-frontend.png — Affinities web app (relationships graph) -->

---

## 3) Start Federation (central registry)

```bash
git clone https://github.com/sci-ndp/ndp-federation.git
cd ndp-federation
cp .env.example .env         # set ADMIN_PASSWORD
docker compose up -d
```

**What you will see:**
- Web: `http://localhost:8020/ui/`
- API & docs: `http://localhost:8020/docs`

<!-- 📸 screenshots/13-federation-ui.png — federation web app (EP list, still empty) -->

---

## 4) Start the NDP-EP (+ backends)

Identical to the common-case install. Configure `.env` to reference the local
AAI, Affinities and Federation instances, and start the data backends with a
Compose profile.

```bash
docker compose --profile full up -d    # Endpoint + MongoDB + MinIO + Kafka
```

**What you will see:** the Endpoint web app at `…/ep-api/ui/`, now wired to your local stack.

---

## ✅ Check: everything is up

```bash
docker ps        # all containers "Up / healthy"
```

The NDP-EP is now reachable two ways:

- **Web UI** — `…/ep-api/ui/`
- **HTTP API** — `…/ep-api/` (interactive docs at `…/ep-api/docs`)

<!-- 📸 screenshots/15-docker-ps.png — list of containers in Up state -->
<!-- note: close Step 1: "installed in minutes; now let's use it". The UI and the
API are the same Endpoint — same data, same permissions. -->

---

# Step 2 — Identity and permissions
### A user signs in and gets a role

---

## Bootstrap the first admin

The Endpoint has **no user store** — identity and roles come from **AAI (Keycloak)**.
How the first admin is created depends on the deployment:

- **🟢 NDP infrastructure (common case)** — register your Endpoint through the NDP
  platform's onboarding process. It provisions the stack and your admin access;
  the platform operators manage identity.
- **🧪 Full stack (self-hosted)** — you assign the admin role yourself in your own
  Keycloak (next slide).

<!-- note: historically the platform onboarding used a federation config_id fed to
a setup script (github.com/sci-ndp/NDP-EP); confirm the current portal/process
with the platform operators. -->

---

## Bootstrap the first admin — full stack

Self-hosted only. In your Keycloak (realm **NDP**) — granting roles from the EP UI
or the AAI API requires an existing admin, so the first one is set here:

1. Create the user and set a password.
2. Assign the realm role **`ndp_admin`** (platform-wide), or **`group:<EP_UUID>:admin`** for this Endpoint only (`EP_UUID` → see appendix *Obtaining the EP_UUID*).

That user can then sign in and manage everyone else via the AAI API / EP.

<!-- 📸 screenshots/19-keycloak-assign-ndp-admin.png — assigning the ndp_admin realm role in Keycloak -->

---

## Where users come from (AAI)

Depends on the deployment:

- **🟢 NDP infrastructure (common case)** — users are existing **nationaldataplatform.com** accounts; they sign in with their NDP identity. You do not create them.
- **🧪 Full stack (self-hosted)** — create them in your own **Keycloak** (Users → Add user → set password). → see appendix *Creating a user — Keycloak*.

> A user alone **cannot publish anything yet** — they still need a **role**.

---

## Requesting access (user)

A new user has **no role**, so the Endpoint denies access — but offers a
**Request access** form with an optional justification.

> Requires `ENABLE_ACCESS_REQUESTS=True`.

---

<!-- _class: imgslide -->

![h:500](screenshots/22-request-access.png)

---

## Approving access (admin)

On the **Access Requests** page, an admin reviews pending requests and **approves**
each with a tier — **Viewer**, **Writer** or **Admin** — or **rejects** it.

> Approval assigns the role; the user re-logs in to pick it up.

---

<!-- _class: imgslide -->

![h:500](screenshots/23-access-requests-approve.png)

---

## The three roles

Roles come from **AAI** and are hierarchical (each tier includes the ones below):

| Role | Can do |
|---|---|
| 👁️ **Viewer** | View and search data. **Read-only.** |
| ✏️ **Writer** | The above **+ create/edit** datasets, resources, and **S3 management**. |
| 🛠️ **Admin** | All of the above **+ administration** (dashboard, access requests). |

> With no role assigned, a user can only see public data. **Secure by default.**

<!-- note: this is the permission model; it reappears live in Step 3. -->

---

# Step 3 — The Endpoint in action
### Search, publish and manage from the web

---

## Search — the landing page

The home page is **Search**, available to **everyone** (including viewers).
Free-text search across **name, description and keywords**.

---

## Search — options

- **Category** — All · Datasets · Services · Organizations
- **Catalog** — **Local** (this Endpoint) or **Global** (the federated NDP catalog)
- **Organization** filter, and **Yours** (only items you own)
- On your own items: **Publish** and **Delete** actions (role/ownership-gated)

---

<!-- _class: imgslide -->

![h:500](screenshots/30-search-ui.png)

---

## Create an organization

From the **"+ New" → Organization** menu, the user creates the organization that
will group their data.

<!-- 📸 screenshots/31-create-organization.png — new organization form -->

---

## Publish a dataset

**"+ New" → Dataset**: the user describes the dataset (title, description, tags…).

<!-- 📸 screenshots/32-create-dataset.png — new dataset form -->

---

## Add a resource

A dataset can have resources of several kinds, all from **"+ New"**:

- **URL** — a link to a file or service
- **S3** — an object in S3-style storage
- **Kafka** — a streaming data flow

<!-- 📸 screenshots/33-create-resource.png — creating a resource (S3/URL/Kafka) -->

---

## Role-based access in practice 🔑

The interface adapts to the authenticated user's role:

- 👁️ **Viewer** — can browse and search; **does not see** "S3 Management" or "+ New".
- ✏️ **Writer** — additionally sees **"+ New"** and **"S3 Management"** (bucket/object management).
- 🛠️ **Admin** — additionally sees the **Dashboard** and **access requests**.

<!-- 📸 screenshots/35-viewer-vs-writer.png — menu comparison: viewer vs writer -->
<!-- note: show the real contrast by opening two sessions (viewer and writer). -->

---

## Storage management (S3) — writers only

**S3 Management** creates and manages buckets and objects.
It is a storage administration tool, restricted to **writers and admins**.

<!-- 📸 screenshots/36-s3-management.png — S3 Management tool (buckets/objects) -->

---

# Step 4 — Automate with Python
### The same operations, from code

<!-- note: for the non-dev audience, frame it as "for power users:
everything in the web can also be automated". -->

---

## The `ndp-ep` library

Every web-app operation is also available **from code** — suitable for automation
and bulk loading.

```bash
pip install ndp-ep
```

> Intended for researchers and teams that load data programmatically.

---

## Example: in a few lines

```python
from ndp_ep import APIClient

# 1. Connect to the Endpoint with your token
client = APIClient(base_url="https://my-endpoint/ep-api", token="…")

# 2. List organizations
print(client.list_organizations())

# 3. Create a dataset and search for it
client.create_dataset(name="measurements-2026", owner_org="my-org")
print(client.search_datasets("measurements"))
```

<!-- 📸 screenshots/40-notebook.png — Jupyter notebook running these steps -->
<!-- note: if time allows, run it live in a notebook and show the result. -->

---

## Web and code: a unified interface

```
   Web (click)   ─┐
                  ├─►  the SAME Endpoint  ─►  the SAME catalog
   Python (code) ─┘
```

> The web interface and the library target the same Endpoint: **identical data and permissions.**

---

# Step 5 — Federation
### The data is discovered elsewhere

---

## The Endpoint registers

Each Endpoint registers with **Federation**. The central registry then tracks its
**status** and **metrics**.

<!-- 📸 screenshots/50-federation-ep-registered.png — the EP appears in the federation -->

---

## Health and metrics

The federation web app reports which Endpoints are **online**, since when, and
their activity.

<!-- 📸 screenshots/51-federation-health.png — EP health/metrics panel -->

---

## Federation benefits

```
        ┌────────────┐
        │ Federation │   registry of all endpoints
        └─────┬──────┘
   ┌──────────┼──────────┐
   ▼          ▼          ▼
[ EP Utah ] [ EP B ]  [ EP C ]     each institution, its catalog
```

> A single search surfaces data from **many** institutions, while each retains
> control of **its own** data.

---

# 🔒 Bonus — NetBird
### The secure network that ties it all together

---

## The problem

In production, each component runs on a **different machine** and must communicate
**without** exposing public ports.

> A **private, encrypted mesh VPN** connects only authorized machines.

---

## The solution: NetBird

- Each machine gets a **stable private IP** on a virtual network.
- Traffic goes **directly and encrypted** between machines (WireGuard).
- Access is restricted to **explicitly authorized peers**; all other traffic is blocked.
- **No public ports** for the services.

<!-- 📸 screenshots/60-netbird-peers.png — NetBird dashboard with connected machines (peers) -->

---

## Demonstrated

Two machines on the network: one **reaches all the NDP services** of the other
(EP, Federation, Affinities, AAI…) **only over the encrypted tunnel**, with no
public ports.

<!-- 📸 screenshots/61-netbird-access.png — proof of access to the services over the mesh -->
> This validates the production multi-machine scenario.

---

# Conclusion

---

## Summary

1. The **NDP-EP** was installed (Docker).
2. The user **authenticated** and received a **role** (both in AAI).
3. Datasets were **published and searched** from the **web app**.
4. The same operations were performed **from code** via the Python library.
5. The data was **federated** and became discoverable across the platform.
6. All components can run over a **secure network** (NetBird).

> **Distributed data, unified discovery, governed and secure access.**

---

## Resources

- **Endpoint (web):** `…/ep-api/ui/` · **API:** `…/ep-api/docs`
- **Federation:** `…:8020/ui/`
- **Affinities:** `…:3000`
- **Python library:** `pip install ndp-ep` · PyPI: `ndp-ep`
- **Repos:** `ep-api`, `ndp-federation`, `ndp-affinities`, `ndp-keycloak-aai-old`, `ndp-ep-py`, `netbird-ndp`

---

# Thank you
## Questions & discussion

<!-- note: open the floor for questions; keep the NetBird technical doc handy. -->

---

# Appendix

---

## Obtaining the EP_UUID — Affinities web app

In the Affinities web app (`http://localhost:3000`, or your Affinities URL):
**Endpoints → Add Endpoint**, fill the form (**Kind** = `ndp-ep`, **URL**, optional
**Metadata**), then **Save**. The new row's **UID** is your `AFFINITIES_EP_UUID`.

![h:300](screenshots/A1-affinities-add-endpoint.png)

---

## Obtaining the EP_UUID — Affinities API

**Via the Affinities API** (`http://localhost:8000`, Swagger at `/docs`):

```bash
# list endpoints and copy your uid
curl http://localhost:8000/ep

# or register this endpoint; the response includes "uid"
curl -X POST http://localhost:8000/ep -H 'Content-Type: application/json' \
  -d '{"kind":"ndp-ep","url":"https://<your-ndp-ep>","metadata":{"name":"My EP"}}'
```

The returned `uid` is your `AFFINITIES_EP_UUID`.

---

## Creating a user — Keycloak

In the Keycloak admin console, realm **NDP**:

1. **Users → Add user** — set **Username** and the required profile fields (email, first/last name), then **Create**.
2. Open the user → **Credentials → Set password** — turn **Temporary** off, then **Save**.

![h:280](screenshots/A2-keycloak-create-user.png)

---

## Assigning groups & roles — AAI API

After the user exists in Keycloak, assign groups/roles via the **AAI API**
(the caller must already be an admin):

```bash
# authenticate as an admin
TOKEN=$(curl -s -X POST "$AAI/user/login" -H 'Content-Type: application/json' \
  -d '{"username":"<admin>","password":"<pass>"}' | jq -r .access_token)

# join the EP group (assigned the viewer role automatically)
curl -s -X POST "$AAI/group/add-user" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"group_name":"<EP_UUID>","username":"<user>"}'
```

---

## Assigning groups & roles — AAI API (cont.)

Upgrade the tier (bare name: `viewer` | `writer` | `admin`):

```bash
curl -s -X POST "$AAI/role/assign" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"groupName":"<EP_UUID>","roleName":"writer","username":"<user>"}'
```

> **First admin exception:** assign `ndp_admin` **directly in Keycloak** — no admin
> exists yet to call this API. The user must re-login for new roles to take effect.
