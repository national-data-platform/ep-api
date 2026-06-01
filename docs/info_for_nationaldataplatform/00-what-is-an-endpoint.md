# What is an NDP Endpoint?

An **NDP Endpoint** (often shortened to **NDP-EP**, or just **EP**) is an
institution's own data-publishing service that plugs into the National Data
Platform. The platform is **federated by design**: instead of every institution
uploading its data to one central place, each institution can run its own
Endpoint that holds its own catalog and storage. An Endpoint's writers can
selectively **publish** datasets and services upstream (through Pre-CKAN) so
they also appear in the central NDP catalog — but the Endpoint itself remains
independent.

## What a single Endpoint provides

An Endpoint is a small, self-contained service that offers:

- **A web app** at `…/ep-api/ui/` where you search, browse, and (with the right
  role) publish datasets, services, and resources.
- **A REST API** at `…/ep-api/` (interactive docs at `…/ep-api/docs`) so the
  same operations can be automated from code or from the
  [`ndp-ep`](https://pypi.org/project/ndp-ep/) Python library.
- **A local catalog** — backed by **CKAN** or **MongoDB** — that stores the
  metadata for the datasets, services, and resources the institution publishes.
- **S3-compatible object storage** (optional) for large files, with a built-in
  **S3 Management** UI for writers and admins.
- **Identity, roles, and access requests** that reuse the user's NDP login
  (CILogon-backed), so users do not create yet another account.
- **Operational link to NDP**: the Endpoint periodically reports its presence
  and operational metrics (status, version, host load, catalog counts) to the
  platform. **Publishing data upstream** to the central catalog is a separate
  per-item action initiated by writers (through Pre-CKAN).

## Where the Endpoint fits in the platform

```
                ┌──────────────────────────────┐
                │   National Data Platform     │   nationaldataplatform.org
                │   (catalog · workspaces ·    │   (CILogon login, central
                │    CollabStudio · …)         │    catalog, JupyterHub …)
                └──────────────┬───────────────┘
                               │ federates · discovers
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
   ┌─────────┐            ┌─────────┐            ┌─────────┐
   │  EP @   │            │  EP @   │            │  EP @   │
   │ Inst. A │            │ Inst. B │            │ Inst. C │
   └─────────┘            └─────────┘            └─────────┘
```

Each Endpoint keeps full control of **its own data and policies**. The central
NDP catalog holds the items that EPs have chosen to publish upstream; the
platform's operational registry simply knows which EPs exist (through their
periodic status reports).

## Who needs an Endpoint?

| If you are… | You typically need… |
|---|---|
| A **researcher**, **educator**, or **student** consuming data on NDP | **No Endpoint.** Use the central NDP at [nationaldataplatform.org](https://nationaldataplatform.org/) to search the catalog, launch workspaces, and download data. |
| A researcher **publishing your own data** through your institution's Endpoint | **No new Endpoint.** Use the EP that your institution already runs — see [Using an Endpoint](01-using-an-endpoint.md). |
| An **institution, lab, or project** that wants to publish its own data into NDP under its own brand and policies | **An Endpoint of your own.** See [For institutional admins](05-for-institutional-admins.md). |

## What the Endpoint is *not*

- Not a place where you create users — identities come from NDP's central
  authentication (CILogon → institutional login).
- Not a copy of the central NDP catalog — the EP holds **your institution's**
  catalog; items only reach the central catalog when a writer chooses to
  publish them upstream.
- Not a replacement for the workspaces / JupyterHub experience — those are
  central NDP services and the EP integrates with them rather than duplicating
  them.

## Related pages

- [Using an Endpoint](01-using-an-endpoint.md) — for researchers and educators.
- [Requesting access and the role tiers](02-requesting-access-and-roles.md) —
  how to be allowed to publish.
- [Publishing data](03-publishing-data.md) — the `+ New` flows.
- [Automating with Python](04-automating-with-python.md) — the `ndp-ep` library.
- [For institutional admins](05-for-institutional-admins.md) — getting an
  Endpoint for your organization.

The source code for the Endpoint API and web app lives at
[github.com/national-data-platform/ep-api](https://github.com/national-data-platform/ep-api).
