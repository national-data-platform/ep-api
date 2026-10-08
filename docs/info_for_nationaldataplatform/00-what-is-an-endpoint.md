# What is an NDP Endpoint?

An **NDP Endpoint** (often shortened to **NDP-EP**, or just **EP**) is a
service an institution runs on its own machine and connects to the National
Data Platform. The platform is **federated by design**: instead of every
institution uploading its data to one central place, each institution can run
its own Endpoint, optionally with its own catalog and storage. An Endpoint's
writers can send datasets to the platform's staging catalog (Pre-CKAN) for
review — but the Endpoint itself remains independent.

In these pages `<endpoint-url>` is the address an Endpoint is served at, for
example `https://ep.my-institution.edu` or `http://<host>:8002`. An operator
can serve it under a path prefix (the `ROOT_PATH` setting, empty by default),
in which case the prefix is part of `<endpoint-url>`.

## What a single Endpoint provides

An Endpoint is a small, self-contained service that offers:

- **A web app** at `<endpoint-url>/ui/` where you search, browse, and (with the
  right role) create datasets, services, and resources.
- **A REST API** at `<endpoint-url>/` (interactive docs at
  `<endpoint-url>/docs`) so the same operations can be automated from code or
  from the [`ndp-ep`](https://pypi.org/project/ndp-ep/) Python library.
- **Search of the NDP global catalog**, always available.
- **A local catalog** (optional) — backed by **MongoDB** or **CKAN** — that
  stores the metadata for the datasets, services, and resources the
  institution publishes. An Endpoint installed with the defaults has none:
  it searches the global catalog and stores nothing locally.
- **S3-compatible object storage** (optional) for large files, with an
  **S3 storage** management page for writers and admins.
- **Kafka topics** (optional), registered as datasets that describe a stream.
- **Identity, roles, and access requests** that reuse the user's NDP account:
  every request is checked against the NDP authentication service, so users
  do not create yet another account.
- **An operational link to NDP** (only when the Endpoint is listed on the
  platform): the Endpoint reports its presence and operational metrics —
  version, host load, public IP, catalog counts and service titles, and which
  integrations are on — to the NDP Federation at startup and every 55
  minutes. Sending a dataset to the staging catalog is a separate, per-dataset
  action taken by a writer.

## Where the Endpoint fits in the platform

```
                ┌──────────────────────────────┐
                │   National Data Platform     │   nationaldataplatform.org
                │   (global catalog, staging   │   (accounts, authentication,
                │    catalog, Federation, …)   │    central catalog, …)
                └──────────────┬───────────────┘
                               │ registers · reports · searches
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
   ┌─────────┐            ┌─────────┐            ┌─────────┐
   │  EP @   │            │  EP @   │            │  EP @   │
   │ Inst. A │            │ Inst. B │            │ Inst. C │
   └─────────┘            └─────────┘            └─────────┘
```

Each Endpoint keeps control of **its own data and policies**. An Endpoint
registered with the **NDP Federation** gets its configuration from it (its
access group and its staging-catalog credentials) and, when it is listed,
reports to it periodically; that is how the platform knows which Endpoints
exist and which are active. An Endpoint can also run **standalone**, without a
registration: it is then not listed and reports nothing.

## Who needs an Endpoint?

| If you are… | You typically need… |
|---|---|
| A **researcher**, **educator**, or **student** consuming data on NDP | **No Endpoint.** Use the central NDP at [nationaldataplatform.org](https://nationaldataplatform.org/) to search the catalog and download data. |
| A researcher **publishing your own data** through your institution's Endpoint | **No new Endpoint.** Use the EP that your institution already runs — see [Using an Endpoint](01-using-an-endpoint.md). |
| An **institution, lab, or project** that wants to publish its own data into NDP under its own name and policies | **An Endpoint of your own.** See [For institutional admins](05-for-institutional-admins.md). |

## What the Endpoint is *not*

- Not a place where you create users — accounts and roles live in NDP's
  authentication service.
- Not a copy of the central NDP catalog — the EP's local catalog, when it has
  one, holds **your institution's** datasets; a dataset reaches the platform
  only when a writer sends it to the staging catalog and it is accepted there.
- Not a replacement for the platform's own services — an Endpoint can show a
  link to a JupyterHub, but it does not run one for users.

## Related pages

- [Using an Endpoint](01-using-an-endpoint.md) — for researchers and educators.
- [Requesting access and the role tiers](02-requesting-access-and-roles.md) —
  how to be allowed in and allowed to publish.
- [Publishing data](03-publishing-data.md) — the `+ New` flows.
- [Automating with Python](04-automating-with-python.md) — the `ndp-ep` library.
- [For institutional admins](05-for-institutional-admins.md) — installing and
  running an Endpoint for your organization.

The source code for the Endpoint API and web app lives at
[github.com/national-data-platform/ep-api](https://github.com/national-data-platform/ep-api).
