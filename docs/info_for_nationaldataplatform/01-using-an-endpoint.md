# Using an Endpoint

If you are a researcher, educator or student on NDP, you do not need to install
anything to use an Endpoint: you sign in with your NDP account and use its web
interface or its API.

## Where you reach an Endpoint

An Endpoint is **its own destination**: you reach it directly at its address,
`<endpoint-url>/ui/` — for example `https://ep.my-institution.edu/ui/` —
given to you by your institution or by whoever shared a dataset hosted on it.

Endpoints are **independent of the central NDP catalog**. A dataset that lives
only in an Endpoint's local catalog is not visible from the central catalog
at [nationaldataplatform.org](https://nationaldataplatform.org/). A writer can
send it to the platform's staging catalog (Pre-CKAN) for review; what happens
to it after that is decided on the platform, not on the Endpoint.

## Signing in

The Endpoint reuses **your existing NDP account**; there is no separate
Endpoint account. The sign-in screen offers two ways in:

- **Paste your NDP access token**, copied from the user section of
  [nationaldataplatform.org](https://nationaldataplatform.org/).
- **Username and password** of your NDP account.

An Endpoint whose operator configured identity-provider sign-in (OIDC) also
shows a button that sends you to the identity provider's login page. The
installer leaves this off, so most Endpoints show only the two options above.

Whichever you use, the Endpoint checks the token with the NDP authentication
service and reads your groups and roles from it (see
[Requesting access and the role tiers](02-requesting-access-and-roles.md)).

**Who may enter** depends on how the Endpoint was set up:

- On an Endpoint **registered with the NDP Federation** (the usual case),
  group-based access is on: only members of the Endpoint's group, and holders
  of the platform-wide `ndp_admin` role, may enter. Anyone else is refused at
  sign-in and, if the Endpoint has access requests enabled, can ask for
  access from that screen.
- On a **standalone** Endpoint, anyone the NDP authentication service accepts
  may enter.

Once in, a user without a role can search and browse; creating or changing
anything needs the writer or admin role.

## The Search experience

The Endpoint's home page is **Search**. You can:

- Type **free text** to search.
- Switch the **category** between **All · Datasets · Services · Organizations**.
- Choose the **catalog**:
  - **Global** (the default) — the NDP global catalog.
  - **Local** — only what this Endpoint's local catalog holds. An Endpoint
    without a local catalog answers this with an error.
- Tick **My assets** to see only items you created; your items carry a
  **Yours** badge.
- From an organization card, list that organization's datasets.

Results expand to show their description, tags, license, version, geographic
extent (when present, drawn on a map) and the **resources** attached to each
dataset. A service card shows the address to call it through the Endpoint
(`<endpoint-url>/services/redirect/<name>`).

## Using a resource

A dataset can carry several kinds of resources:

- **URL resources** — a link to a file or service (CSV, JSON, NetCDF, a
  stream, …). Open or download it from the link.
- **S3 resources** — a pointer (`s3://bucket/path` or an `http(s)` URL) to an
  object in S3-compatible storage. Temporary download links (presigned URLs)
  are created from the Endpoint's **S3 storage** page, which needs the writer
  role.
- **Kafka topics** — a streaming data flow. The dataset lists the broker
  host, port and topic so you can connect with a Kafka client.

## What if you want to publish?

If you have no role, or only the viewer role, the Endpoint shows your search
results but not the **`+ New`** menu, which is also where the S3 storage page
is reached. To publish, you need the writer role — see
[Requesting access and the role tiers](02-requesting-access-and-roles.md).

## Want to automate?

Anything you do through the web app is also available through the Endpoint's
HTTP API (interactive documentation at `<endpoint-url>/docs`) and through the
[`ndp-ep`](https://pypi.org/project/ndp-ep/) Python library. See
[Automating with Python](04-automating-with-python.md).
