# Publishing a dataset

Where a dataset goes, who is asked for permission along the way, and which
switch stops it. Drawn against an Endpoint with everything switched on — a
local catalog and the staging catalog both configured — with each gate marked,
so the same picture explains an Endpoint where one of them is off.

The three catalogs are not three destinations to choose from. A dataset is
**registered** in the local catalog, **promoted** from there to the staging
catalog for review, and the **global** catalog is read-only: nothing is ever
published to it from an Endpoint.

## The sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant EP as Endpoint API
    participant AAI as Authentication service
    participant Local as Local catalog<br/>(MongoDB or CKAN)
    participant Pre as Staging catalog<br/>(CKAN)
    participant Global as Global catalog<br/>(CKAN, read-only)

    rect rgb(245, 245, 245)
    Note over User,Local: Registering — the dataset is created in the local catalog
    User->>EP: POST /dataset + Bearer token
    Note over EP: Route mounted only when a local catalog exists<br/>and CKAN_LOCAL_ENABLED is True — otherwise 404
    EP->>AAI: validate the token
    AAI-->>EP: identity, groups and roles
    Note over EP: Writer or admin required, and membership of<br/>GROUP_NAMES when group access is on — otherwise 403
    EP->>Local: package_create
    Local-->>EP: dataset id
    Note over EP,Local: A name already taken is retried once with a<br/>timestamp suffix, and the caller is told
    EP-->>User: 201 with the id
    end

    rect rgb(238, 242, 248)
    Note over User,Pre: Promoting — a copy goes to the staging catalog for review
    User->>EP: POST /dataset/{id}/publish
    Note over EP: PRE_CKAN_ENABLED must be True — otherwise 400,<br/>"PRE-CKAN is disabled and cannot be used"
    EP->>AAI: validate the token
    AAI-->>EP: identity, groups and roles
    EP->>Local: package_show — read the dataset back
    Local-->>EP: metadata and resources
    Note over EP: System fields dropped. owner_org becomes<br/>PRE_CKAN_ORGANIZATION when set, otherwise the<br/>organization's name is resolved from the local catalog
    EP->>Pre: package_create, marked as submitted for review
    alt the name is already taken there
        Pre-->>EP: "That name is already in use"
        EP->>Pre: retry with a timestamp suffix
        Pre-->>EP: created, under the new name
    else the organization does not exist there
        Pre-->>EP: "Organization does not exist"
        EP-->>User: 400 — create it in the staging catalog first
    end
    Pre-->>EP: dataset id
    EP->>Local: mark the local copy as submitted
    Note over EP,Local: A failure here is logged and swallowed:<br/>it must not undo the copy already created
    EP-->>User: 201, with a warning if it was renamed
    end

    rect rgb(245, 245, 245)
    Note over User,Global: The global catalog is read-only
    User->>EP: GET /search?server=global
    EP->>Global: package_search
    Global-->>EP: results
    EP-->>User: 200
    Note over EP,Global: There is no route that writes here. Datasets reach<br/>the platform by being reviewed in staging, not by<br/>being pushed from an Endpoint
    end
```

## What stops it, and how you can tell

Each of these fails differently on purpose — the status code says which switch
is closed.

| Configuration | Registering locally | Promoting to staging |
|---|---|---|
| Everything on | Works | Works |
| `PRE_CKAN_ENABLED=False` | Works | **400** — "PRE-CKAN is disabled and cannot be used" |
| `CKAN_LOCAL_ENABLED=False` | **404** — the route is not mounted | **404** — same |
| `LOCAL_CATALOG_BACKEND=none` | **404** — nothing to write to | **404** |
| Group access on, user outside the group | **403** | **403** |
| User with no writer or admin role | **403** | **403** |

The two 404s surprise people: the routes are *absent* rather than answering an
error, so they do not appear in `/docs` either. That is deliberate — an
Endpoint should not advertise operations it cannot perform — but it means a
call gets the same answer as a typo in the path.

## What each install produces

The installer decides these switches for you:

| Install | Local catalog | Staging |
|---|---|---|
| No catalog, no registration | Nothing to register into — the routes are absent | Off: no URL, no credentials |
| No catalog, registered | Same | Configured, but unreachable through the absent routes |
| MongoDB or CKAN, no registration | Works | Off — the credentials come from a registration |
| MongoDB or CKAN, registered | Works | Works, with the token the registration minted |

The staging catalog's URL and API token are not something to fill in by hand:
the Federation mints that token during registration, using the operator's own
access token. An Endpoint that never registered has no way to obtain one.

`PRE_CKAN_ORGANIZATION` is a separate matter and is optional. It overrides the
`owner_org` of everything promoted, which is needed when the staging
credentials are tied to one organization. Left empty, the dataset keeps its own
organization, resolved to its name.

## Related

- [Installing a standalone Endpoint with no catalog](installing-standalone-no-catalog.md)
- [Installing an Endpoint registered with the Federation](installing-registered-no-catalog.md)
- [Roles and permissions](../roles-and-permissions.md) — who counts as a writer
- [Configuration reference](../configuration.md) — every switch named above
