# Roles and permissions

This document explains the role model the Endpoint (EP) enforces, how a
user's roles travel from Keycloak into the token, and the exact steps to
grant access or introduce a new role. It is aimed at deployment
operators and at NDP support.

> TL;DR
> - The EP understands three tiers: **viewer** (read), **writer**
>   (modify catalog content and use S3) and **admin** (everything).
>   The identity provider's **editor** role counts as writer.
> - Roles are Keycloak **realm roles** named either `ndp_{tier}`
>   (platform-wide) or `group:{group}:{tier}` (per-Endpoint), where
>   `{group}` is one of the Endpoint's `GROUP_NAMES` entries or a form of
>   `AFFINITIES_EP_UUID`.
> - Assigning an existing tier to a user is **configuration only** (AAI
>   API or the Access Requests screen). A genuinely new permission level
>   requires an **Endpoint code change** (see
>   [Scenario B](#scenario-b-a-brand-new-permission-level)).

All of the matching logic is in
[`api/services/auth_services/authorization_service.py`](../api/services/auth_services/authorization_service.py).
How a request reaches it is described in
[architecture/overview.md](architecture/overview.md#4-how-a-request-flows).

---

## 1. The three tiers

| Tier   | Can do | Implied lower tiers |
| ------ | ------ | ------------------- |
| viewer | Use the `/pelican/*` read routes. (Catalog search and resource reads need no role at all.) | — |
| writer | Everything a viewer can, plus every create / update / delete / publish route of the catalog, all `/s3/*` routes, `/status/rexec` and `/pelican/import-metadata`. | viewer |
| admin  | Everything a writer can, plus listing, approving and rejecting access requests. | writer, viewer |

The tiers are hierarchical: an **admin** does not also need the writer
and viewer roles, and a **writer** does not also need viewer. The
Endpoint resolves the highest tier the user holds.

**Strict default:** an authenticated user who holds **no** recognised
role resolves to `none`. They can sign in to the UI (when they pass the
group gate below), search the catalogs and read resources, and nothing
else: every route guarded by a tier answers `403`.

### The group gate

With `ENABLE_GROUP_BASED_ACCESS=True` an extra check runs **before** the
tier check on `/user/info` (which the UI uses to let a user in), on every
writer route, on every `/s3/*` route and on every `/pelican/*` route. The
user passes it when any of these holds:

1. they hold `ndp_admin`;
2. they are a member of the group named `AFFINITIES_EP_UUID`;
3. they are a member of one of the `GROUP_NAMES` groups.

Group names are compared case-insensitively, ignoring leading and
trailing slashes. With the gate on and `GROUP_NAMES` empty, only the first
two pass. The admin-only access-request routes check the admin tier only,
not the gate.

---

## 2. Role naming convention

Every recognised role is a Keycloak **realm role**. Role names are
compared case-insensitively, with surrounding whitespace ignored and the
group path normalised (`group:/ndp_ep/ep-1:admin` equals
`group:ndp_ep/ep-1:admin`).

| Tier   | Platform-wide (any EP)        | Per-endpoint                                  |
| ------ | ----------------------------- | --------------------------------------------- |
| admin  | `ndp_admin`                   | `group:{G}:admin`                             |
| writer | `ndp_writer`, `ndp_editor`    | `group:{G}:writer`, `group:{G}:editor`        |
| viewer | `ndp_viewer`                  | `group:{G}:viewer`                            |

`{G}` is any of:

- each entry of `GROUP_NAMES` — on an Endpoint registered through the
  Federation this is `ndp_ep/ep-<config-id>`, so its roles look like
  `group:ndp_ep/ep-<config-id>:writer`;
- when `AFFINITIES_EP_UUID` is set to `<uuid>`: `<uuid>`,
  `ndp_ep/<uuid>` and `ndp_ep/ep-<uuid>` (the last two only when the
  value contains no `/`, and the `ep-` form only when it does not already
  start with `ep-`).

The legacy per-EP admin form `{AFFINITIES_EP_UUID}_admin` (no `group:`
prefix, underscore before `admin`) is **also** still accepted for admin.

> **"editor" and "writer".** The identity provider names the write tier
> `editor` (its default group roles are `admin` / `editor` / `viewer`);
> the Endpoint names it `writer`. Both are accepted for the writer tier,
> so assigning the AAI's `editor` role grants write access on the EP.

Any realm role that does not match one of the names above is carried in
the token but **ignored** by the EP for permission purposes.

---

## 3. How the Endpoint sees roles

On every authenticated request the EP sends the bearer token to
`AUTH_API_URL` and receives the user's `roles` and `groups` (see
[`get_current_user.py`](../api/services/auth_services/get_current_user.py)).
`GET /user/info` returns that payload plus two derived fields:

```jsonc
GET /user/info
{
  "username": "raul",
  "sub": "6bfaa6c3-…",
  "roles": ["group:ndp_ep/ep-123:admin", "default-roles-ndp"],
  "groups": ["/ndp_ep/ep-123"],
  "ndp_user_id": "<16 hex chars>",     // first 16 hex chars of SHA-256(sub)
  "effective_role": "admin"            // admin | writer | viewer | none
}
```

The functions and dependencies in
[`authorization_service.py`](../api/services/auth_services/authorization_service.py):

- `is_admin`, `is_writer`, `is_viewer` — tier checks (each implies the
  lower tiers).
- `effective_role` — returns the highest tier as a string; the UI uses it
  to decide which actions to show.
- `check_group_membership` — the group gate.
- `get_user_for_endpoint_access` — group gate only; guards `/user/info`.
- `get_user_for_read_operation` — group gate plus viewer tier; guards
  every `/pelican/*` route (declared on the Pelican router).
- `get_user_for_write_operation` — group gate plus writer tier; guards
  every catalog `POST`/`PUT`/`PATCH`/`DELETE`, `POST /dataset/{id}/publish`,
  all `/s3/*` routes (including the `GET`s), `GET /status/rexec` and
  `POST /pelican/import-metadata`.
- `require_admin` — admin tier only; guards
  `GET /user/access-requests` and the approve and reject routes.

The token `TEST_TOKEN` (default `testing_token`) bypasses the AAI and is
treated as a user holding `ndp_admin`. Set it blank on any Endpoint others
can reach; see [configuration.md](configuration.md#test_token).

---

## 4. How roles reach the token

> This section describes Keycloak and the AAI, which live outside this
> repository. It is kept from the previous revision of this document and
> was not re-verified against their code for this one.

Roles are emitted into the token by a **protocol mapper** on the
Keycloak client (`oidc-usermodel-realm-role-mapper`, claim name
`roles`), configured when the client is created by the AAI.

Because the mapper emits the user's realm roles wholesale, a newly
created `group:{G}:…` role appears in the token as soon as it is assigned
— no per-role client change, no client-scope edit. Assigning a role to a
user does not change a token that was already issued: the user must sign
in again to get one that carries it.

The only situation where the client *would* matter is a deployment whose
client was created **without** the realm-roles mapper, or one relying on
client-specific roles (`resource_access.{client}.roles`) instead of
realm roles.

---

## 5. AAI API for role and group management

The AAI API (base URL = scheme and host of `AUTH_API_URL`) is
authoritative for group and role writes. The Endpoint uses three of its
operations, always with the calling administrator's own bearer token
([`aai_client.py`](../api/services/auth_services/aai_client.py)):

| Action | Endpoint | Body the Endpoint sends |
| ------ | -------- | ----------------------- |
| Add user to a group | `POST /group/add-user` | `{"group_name": "<group>", "username": "<user>"}` |
| Assign a role to a user | `POST /role/assign` | `{"role_name": "<tier>", "username": "<user>", "group_name": "<group>"}` |
| List group members | `GET /group/members?group_name=<group>` | — |

`role_name` is the **bare** tier (`writer`, `admin`); the AAI builds
`group:{group}:{tier}` itself, and passing the fully qualified name makes
it double-prefix. AAI answers 400/401 become 401, 403 stays 403, 404
stays 404, anything else and an unreachable AAI become 502.

The AAI offers more operations (creating and deleting custom roles,
removing a role from a user) that the Endpoint does not call; their
request formats are defined by the AAI, not by this repository.

---

## 6. Common tasks

### Grant an existing tier to a user

**Via the UI (preferred).** With `ENABLE_ACCESS_REQUESTS=True`, a user
without access requests it from the login screen, and an admin approves
it on the **Access Requests** page, picking the tier (Viewer / Writer /
Admin). The Endpoint then calls the AAI with the admin's token:

- **viewer** — `POST /group/add-user` only (the AAI assigns viewer on
  join, according to the approve route's documentation);
- **writer** / **admin** — `POST /group/add-user`, then
  `POST /role/assign` with the bare tier.

The group used is the **first `GROUP_NAMES` entry**, or
`AFFINITIES_EP_UUID` when `GROUP_NAMES` is empty; with neither, approval
answers 503 (since 0.34.46 — up to 0.34.45 it always used
`AFFINITIES_EP_UUID` and answered 503 when that was empty, which is how
the installer leaves it). `member` is accepted as a deprecated alias for
`viewer`.

**Via the AAI API.** Add the user to the group, then assign a higher tier
if needed. The bodies below are the ones the Endpoint itself sends:

```bash
TOKEN=$(curl -s -X POST "$AAI/user/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"<admin>","password":"<pass>"}' | jq -r .access_token)

# join the group
curl -s -X POST "$AAI/group/add-user" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"group_name":"<GROUP>","username":"<user>"}'

# give the writer tier on that group (bare tier name)
curl -s -X POST "$AAI/role/assign" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"role_name":"writer","username":"<user>","group_name":"<GROUP>"}'
```

`<GROUP>` is the Endpoint's group as configured in `GROUP_NAMES` (for a
registered Endpoint, `ndp_ep/ep-<config-id>`). The user must **sign in
again** afterwards: their old token was issued before the grant.

### Scenario A: reuse an existing tier in another group

Nothing in the Endpoint changes. Assign the
`group:{OTHER}:viewer|writer|admin` roles for that group. An Endpoint
only evaluates per-Endpoint roles for its own `GROUP_NAMES` entries and
`AFFINITIES_EP_UUID` forms, so roles on other groups grant nothing there
(the platform-wide `ndp_*` roles apply everywhere).

### Scenario B: a brand-new permission level

If you need a tier that is **not** viewer/writer/admin (say, a
`publisher` that can publish but not delete), two things are required:

1. **Create the role** in Keycloak / via the AAI as usual
   (`group:{G}:publisher`). It will appear in the token automatically
   (Section 4).
2. **Teach the Endpoint about it** — a code change in
   [`authorization_service.py`](../api/services/auth_services/authorization_service.py):
   add a matcher (e.g. `is_publisher`, built like `is_writer` on
   `endpoint_group_role_names("publisher")`), fold it into
   `effective_role`, and use it in a dependency on the relevant routes.
   Without this step the role rides in the token but grants nothing.

---

## 7. When to request NDP support

Open a request with NDP support when you need something that is not a
plain assignment of an existing tier:

- A new permission level that the Endpoint must enforce (Scenario B).
- Changes to the Keycloak client itself (new protocol mappers, switching
  to client roles) — only relevant for non-standard clients (Section 4).
- Realm-level changes you do not have admin rights for.

For everything else — granting viewer/writer/admin to a user, listing
members — use the Access Requests screen or the AAI API directly.
