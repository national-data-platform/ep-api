# Registering, reaching and publishing a service

A service is a dataset that points at something running: an API, a UI, a
trigger. Registering one puts it in the Endpoint's catalog; the Endpoint can
then be used to reach it; and promoting it offers it to the platform for
review.

Drawn against an Endpoint with a local catalog and the staging catalog
configured — a registered install with MongoDB or CKAN.

## The sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant EP as Endpoint API
    participant AAI as Authentication service
    participant Local as Local catalog
    participant Svc as The service itself
    participant Pre as Staging catalog

    rect rgb(245, 245, 245)
    Note over User,Local: Registering
    User->>EP: POST /services + Bearer token
    Note over User,EP: owner_org must be "services" — the organization the<br/>Endpoint creates for them at startup. Anything else<br/>is refused by the request model
    EP->>AAI: validate the token
    AAI-->>EP: identity, groups and roles
    Note over EP: A write: writer or admin, and the group when<br/>group-based access is on
    EP->>Local: package_create in "services",<br/>with a resource of format "service" holding the URL
    Local-->>EP: id
    EP-->>User: 201 with the id
    end

    rect rgb(238, 242, 248)
    Note over User,Svc: Reaching it — a proxy, not a redirect
    User->>EP: GET /services/redirect/{name}
    Note over User,EP: No token required: this route has no<br/>authentication of its own
    EP->>Local: search "services" for that name
    alt not found
        Local-->>EP: nothing
        EP-->>User: 404 — Service '{name}' not found
    else found
        Local-->>EP: the dataset, with the service URL
        EP->>Svc: the same request, forwarded
        Note over EP,Svc: Sent from inside the Endpoint's container:<br/>a URL that works from your shell may not<br/>resolve from there
        alt the service answers
            Svc-->>EP: its response
            EP-->>User: that response, passed through
        else it cannot be reached
            EP-->>User: 502 — Unable to connect to the target service
        end
    end
    Note over User,Svc: /services/redirect/{name}/{path} forwards the<br/>subpath too, for GET, POST, PUT, PATCH and DELETE
    end

    rect rgb(245, 245, 245)
    Note over User,Pre: Publishing it for review
    User->>EP: POST /dataset/{name}/publish + Bearer token
    Note over EP: PRE_CKAN_ENABLED must be True — otherwise 400
    EP->>Local: package_show
    Local-->>EP: the service, resources and extras
    Note over EP: owner_org is replaced by PRE_CKAN_ORGANIZATION.<br/>Without it the local organization travels along and<br/>the staging catalog refuses the write
    EP->>Pre: package_create, marked "status: submitted"
    Pre-->>EP: id
    EP->>Local: mirror "status: submitted" locally
    EP-->>User: 201
    end
```

## The three things that catch people out

**`owner_org` must be `services`.** Not the Endpoint's organization, not the
user's. The request model validates it against that exact string, and the
Endpoint creates that organization for itself at startup. Services live
together there, which is also how the redirect finds them.

**The redirect is a proxy.** `/services/redirect/{name}` does not answer 302
and does not send the caller to the service. The Endpoint forwards the request
and returns what comes back, so the caller only ever talks to the Endpoint. Two
consequences worth planning for:

- The request leaves from **inside the Endpoint's container**. A service at
  `http://localhost:8002` — the Endpoint's own published port — is not
  reachable from there, and the answer is `502 Unable to connect to the target
  service`. Register the address the container can resolve.
- The route takes **no token**. Whoever can reach the Endpoint can reach the
  service through it, whatever the service's own access rules are. If that is
  not what you want, the service has to enforce its own.

**Publishing needs an organization the staging catalog will accept.** A
promoted dataset keeps its local organization unless `PRE_CKAN_ORGANIZATION`
says otherwise, and `services` is not an organization the staging credentials
own. The failure is an authorization error naming a user, which reads as a
credentials problem:

```
Access denied: User <user> not authorized to add dataset to this organization
```

The installer sets that value from the registration — `ep-<config-id>`, the
organization the Federation minted the staging token for — and checks with the
staging catalog that it is accepted before writing anything. An Endpoint
installed before that, or configured by hand, needs it set.

## What it looks like end to end

```bash
# 1. Register
curl -X POST http://localhost:8002/services \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"service_name":"my-service","service_title":"My service",
       "owner_org":"services","service_url":"https://example.org/api",
       "service_type":"API"}'
# 201 {"id":"0300b047-..."}

# 2. Reach it — no token
curl http://localhost:8002/services/redirect/my-service
# 200, with whatever the service answered

# 3. Publish it for review
curl -X POST http://localhost:8002/dataset/my-service/publish \
  -H "Authorization: Bearer $TOKEN"
# 201 {"id":"86551d66-...","message":"Dataset published to PRE-CKAN successfully"}
```

`service_type` is one of **API**, **UI** or **Trigger**, and the service can
also carry a health-check URL, documentation URL and notes.

## Related

- [Publishing a dataset](publishing-a-dataset.md) — the same promotion, for data
- [Installing an Endpoint registered with the Federation](installing-registered-no-catalog.md) — where the staging credentials come from
- [Roles and permissions](../roles-and-permissions.md) — who may register one
