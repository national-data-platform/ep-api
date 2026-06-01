# Using an Endpoint

If you are a researcher, educator or student on NDP, you do not need to install
anything to use an Endpoint: you reach it through your normal NDP login and use
its web interface or its API.

## How you arrive at an Endpoint

There are two common routes:

1. **From the central NDP catalog.** When you search at
   [nationaldataplatform.org](https://nationaldataplatform.org/), the federation
   surfaces datasets and services exposed by every Endpoint. Following a result
   from a particular institution takes you to that institution's Endpoint web
   app.
2. **Directly at your institution's Endpoint URL.** If your institution runs an
   Endpoint, your IT or data team will give you a URL like
   `https://<your-institution>/ep-api/ui/`. You can bookmark it.

## Signing in

The Endpoint reuses **your existing NDP identity**. You log in through
**CI Logon** with your **institutional account** — the same flow as the central
NDP. You do not create a separate Endpoint account, and commercial emails
(Gmail, Outlook, etc.) are not eligible.

Once you are logged in, the Endpoint reads your identity and your role (more on
roles in [Requesting access and the role tiers](02-requesting-access-and-roles.md)).
A user without a role can still **see and search public data**; write actions
require an explicit role.

## The Search experience

The Endpoint's home page is **Search**. You can:

- Type **free text** to match across **name, description and keywords**.
- Switch the **category** between **All · Datasets · Services · Organizations**.
- Choose the **catalog scope**:
  - **Local** — only what this Endpoint publishes.
  - **Global** — the federated NDP catalog (results from many Endpoints).
- Filter by **organization** or toggle **Yours** to see only items you own.

Results expand to show their description, tags, license, version, geographic
extent (when present, drawn on a map) and the **resources** attached to each
dataset.

## Using a resource

A dataset can carry several kinds of resources, and each kind opens in the way
you expect:

- **URL resources** — a link to a file or service (CSV, JSON, NetCDF, …). Click
  to open or download.
- **S3 resources** — a pointer to an object in S3-compatible storage. The
  Endpoint can generate a temporary **presigned URL** so you can fetch the
  object without having direct S3 credentials.
- **Kafka topics** — a streaming data flow. The dataset page lists the broker
  host, port and topic so you can connect with a Kafka client.

## What if you want to publish?

If your role is **read-only** ("viewer", or no role at all), the Endpoint will
show your search results but will not show the **`+ New`** menu or the S3
Management entry. To publish, you need to **request access** — see
[Requesting access and the role tiers](02-requesting-access-and-roles.md).

## Want to automate?

Anything you do through the web app is also available through the Endpoint's
HTTP API (`/ep-api/docs` for interactive documentation) and through the
[`ndp-ep`](https://pypi.org/project/ndp-ep/) Python library. See
[Automating with Python](04-automating-with-python.md).
