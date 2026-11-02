# Roles and permissions

This document explains who may do what on an Endpoint (EP), how the EP
finds out, and the exact steps to grant access or introduce a new
permission level. It is aimed at deployment operators and at NDP support.

> TL;DR
> - The EP understands three tiers: **viewer** (read), **writer**
>   (modify catalog content and use S3) and **admin** (everything).
>   The identity provider calls the writer tier **editor**.
> - **Keycloak decides.** For every guarded route the EP asks Keycloak,
>   with the caller's own token, whether they pass a gate of the
>   Endpoint's client (`ep-<config-id>`): `admin-area`, `editor-area` or
>   `viewer-area`. The roles and groups the AAI API reports are not
>   used for permissions.
> - A user's tier is their **level in the Endpoint's group**
>   (`ndp_ep/ep-<config-id>`): its `admins`, `editors` or `viewers`.
>   `ndp_admin` passes every gate of a client the AAI created.
> - Granting a tier is **configuration only** (Access Requests screen or
>   AAI API). A genuinely new permission level needs an **Endpoint code
>   change** (see [Scenario B](#scenario-b-a-brand-new-permission-level)).

Everything is in
[`ep_access_gate.py`](../api/services/auth_services/ep_access_gate.py):
`ep_access_gate`, the decision call, with the same name and the same
raise-unless-granted behaviour as the Federation's
`app/services/ep_access_gate.py`, and the three route dependencies built on
it, `ep_admin_gate`, `ep_editor_gate` and `ep_viewer_gate`. How a request
reaches them is described in
[architecture/overview.md](architecture/overview.md#4-how-a-request-flows).

---

## 1. The three tiers

| Tier   | Gate          | Passed by the group's | Can do |
| ------ | ------------- | --------------------- | ------ |
| viewer | `viewer-area` | admins, editors, viewers | Use the `/pelican/*` read routes. (Catalog search and resource reads need no tier at all.) |
| writer | `editor-area` | admins, editors | Everything a viewer can, plus every create / update / delete / publish route of the catalog, all `/s3/*` routes, `/status/rexec` and `/pelican/import-metadata`. |
| admin  | `admin-area`  | admins | Everything a writer can, plus listing, approving and rejecting access requests. |

The tiers nest: an admin passes `editor-area` and `viewer-area` too, so
nobody needs more than one level. A level on a **parent group** counts
too, if that level's subgroup existed when the client's gates were set up
(the gates list the subgroups by id). The realm role `ndp_admin` passes all
three gates of a client the AAI created with `/client/create`; a client linked later with the AAI's `tools/adopt_client.py` has no `ndp_admin` policy.

**Strict default:** an authenticated user Keycloak grants no gate resolves
to `none`. Every route guarded by a tier answers them `403`; catalog
searches and resource reads stay public.

### The entry check

On an Endpoint with a client (`AUTHZ_CLIENT_ID`), `GET /user/info` (which
the UI uses to let a user in) also requires a tier, i.e. `viewer-area`, so
a user with no level on the Endpoint cannot enter the UI and is offered the
access-request form instead. Without a client, any authenticated user
enters.

---

## 2. How the Endpoint asks

Registering through the Federation creates the Endpoint's Keycloak client
`ep-<config-id>` linked to its group `ndp_ep/ep-<config-id>`; the AAI API
turns the group's levels into the three gates (resources with policies on
that client). The installer writes the client to `AUTHZ_CLIENT_ID`.

For each guarded request the EP sends, with the caller's bearer token:

```http
POST <realm>/protocol/openid-connect/token
Authorization: Bearer <caller's token>
Content-Type: application/x-www-form-urlencoded

grant_type=urn:ietf:params:oauth:grant-type:uma-ticket
&audience=<AUTHZ_CLIENT_ID>
&permission=editor-area
&response_mode=decision
```

`<realm>` is `<KEYCLOAK_URL>/realms/<AUTHZ_REALM>` (default
`https://idp.nationaldataplatform.org/realms/NDP`). This is the same request the Federation makes
to protect `GET /ep/{config_id}`. No client secret is involved.

| Keycloak answers | The EP answers |
| ---------------- | -------------- |
| `200 {"result": true}` | the request goes through |
| `403` (denied), `400` (no such client or gate), anything else | `403` |
| `401` (token not accepted) | `401` |
| `5xx` or unreachable | `502` |

Without `AUTHZ_CLIENT_ID` nothing is asked: guarded routes answer `403`
and `effective_role` is `none`.

Keycloak reads group membership live, so a grant takes effect on the
user's next request; they do not have to sign in again. A removal can lag
until the user's token expires, as long as the client's role-based
policies read roles from the token rather than from the user.

---

## 3. What the Endpoint reports

Identity still comes from the AAI API: on every authenticated request
the EP sends the bearer token to `<KEYCLOAK_URL>/api/information` and
receives `sub`, `username` and, informationally, `roles`, `groups` and
`clientRoles` (see
[`get_current_user.py`](../api/services/auth_services/get_current_user.py)).
On every route that needs a tier, Keycloak's decision call checks the token
as well.
`GET /user/info` returns that payload plus two derived fields:

```jsonc
GET /user/info
{
  "username": "raul",
  "sub": "6bfaa6c3-…",
  "roles": ["group:ndp_ep/ep-123:admin", "default-roles-ndp"],  // not used for permissions
  "groups": [{"id": "…", "path": "/ndp_ep/ep-123/admins", "name": "admins"}],  // not used
  "clientRoles": {},                                            // not used for permissions
  "ndp_user_id": "<16 hex chars>",     // first 16 hex chars of SHA-256(sub)
  "effective_role": "admin"            // admin | writer | viewer | none, from the gates
}
```

`effective_role` asks `admin-area`, `editor-area`, `viewer-area` in that
order and reports the first tier that passes; the UI uses it to decide
which actions to show. With the entry check on, `/user/info` refuses a
caller whose `effective_role` is `none`.

The route dependencies, each returning the user:

- `ep_viewer_gate` (`viewer-area`) — every `/pelican/*` route (declared on
  the Pelican router).
- `ep_editor_gate` (`editor-area`) — every catalog
  `POST`/`PUT`/`PATCH`/`DELETE`, `POST /dataset/{id}/publish`, all
  `/s3/*` routes (including the `GET`s), `GET /status/rexec` and
  `POST /pelican/import-metadata`.
- `ep_admin_gate` (`admin-area`) — `GET /user/access-requests` and the
  approve and reject routes.

`TEST_TOKEN`, when set, is a token that bypasses the AAI and Keycloak and
passes every gate. It is empty (off) by default; set it only for local
development, never on an Endpoint others can reach; see
[configuration.md](configuration.md#test_token).

---

## 4. AAI API for group management

The AAI API (`<KEYCLOAK_URL>/api`) is
authoritative for group writes. Approving an access request makes one
call, with the approving administrator's own bearer token
([`aai_client.py`](../api/services/auth_services/aai_client.py)):

| Action | Endpoint | Body the Endpoint sends |
| ------ | -------- | ----------------------- |
| Add user to a group at a level | `POST /group/add-user` | `{"group_name": "<group>", "username": "<user>", "role": "viewer\|editor\|admin"}` |

`/group/add-user` makes the user a member of the group, assigns the realm
role `group:<group>:<level>` and puts the user in the level's subgroup
(`<group>/viewers`, `/editors`, `/admins`), which is what the gates are
decided on. The subgroup step is best effort: if it fails the AAI still
answers 200 and only logs it. `/role/assign` sets only the realm role, so
on its own it grants nothing on the Endpoint.

The AAI decides who may call it by the caller's own **realm roles**, not by
their level subgroups: `group:<group or a parent>:editor` or `:admin`, or
`ndp_admin`; granting `admin` needs `group:<group>:admin` or `ndp_admin`.
An administrator added to `<group>/admins` by hand in the Keycloak console
passes `admin-area` on the Endpoint but is refused by the AAI ("Forbidden:
insufficient group privileges") until they also hold that realm role;
`/group/add-user` with `role` `admin` gives both. AAI answers 400/401
become 401, 403 stays 403, 404 stays 404, anything else and an unreachable
AAI become 502.

---

## 5. Common tasks

### Grant an existing tier to a user

**Via the UI (preferred).** With `ENABLE_ACCESS_REQUESTS=True`, a user
without access requests it from the login screen, and an admin approves
it on the **Access Requests** page, picking the tier (Viewer / Writer /
Admin). The Endpoint then calls `POST /group/add-user` with the admin's
token at the matching level: `viewer`, `editor` for writer, or `admin`.

The group used is the one the client is linked to,
`ndp_ep/<AUTHZ_CLIENT_ID>`; without `AUTHZ_CLIENT_ID`, approval answers
503. `member` is accepted as a deprecated alias for `viewer`.

**Via the AAI API.** The body below is the one the Endpoint itself sends:

```bash
AAI=https://idp.nationaldataplatform.org/api   # <KEYCLOAK_URL>/api
TOKEN=$(curl -s -X POST "$AAI/user/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"<admin>","password":"<pass>"}' | jq -r .access_token)

# make <user> an editor (the writer tier) of the Endpoint's group
curl -s -X POST "$AAI/group/add-user" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"group_name":"ndp_ep/ep-<config-id>","username":"<user>","role":"editor"}'
```

The grant applies from the user's next request.

### Check what Keycloak decides for a user

With the user's token in `$USER_TOKEN`:

```bash
curl -s -X POST "https://<idp>/realms/NDP/protocol/openid-connect/token" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d grant_type=urn:ietf:params:oauth:grant-type:uma-ticket \
  -d audience=ep-<config-id> -d permission=editor-area -d response_mode=decision
# {"result":true} — or a 403 with "not_authorized"
```

A `400` instead means the client does not exist or has no such gate: an
Endpoint registered before the Federation linked clients to groups has a
client without gates, and every user is refused until NDP support links
it (the AAI's `tools/adopt_client.py`, which also moves holders of the old
`group:<group>:<level>` realm roles into the level subgroups). A client
linked that way gets no `ndp_admin` policy.

### Scenario A: reuse an existing tier in another group

Nothing in the Endpoint changes. Add the user at a level of a **parent**
group of `ndp_ep/ep-<config-id>` (e.g. `ndp_ep`) and Keycloak counts it on
every Endpoint below whose gates were set up after that level's subgroup
existed; for older clients the gates have to be set up again (NDP support).
A level on an unrelated group grants nothing here.

### Scenario B: a brand-new permission level

If you need a tier that is **not** viewer/writer/admin (say, a
`publisher` that can publish but not delete), two things are required:

1. **Create the level** on the Endpoint's group through the AAI API
   (`customPermissions` on `/client/create`; for a client that already
   exists, ask NDP support). The AAI adds a `publisher-area` gate to the
   client, passed by the level's members and by the group's admins.
2. **Teach the Endpoint about it** — a code change: add
   `ep_publisher_gate`, built like `ep_editor_gate` but asking
   `ep_access_gate(token, "publisher-area")`, to
   [`ep_access_gate.py`](../api/services/auth_services/ep_access_gate.py),
   use it on the relevant routes and, if the UI should know, fold it into
   `_effective_role` in
   [`user_info.py`](../api/routes/user_routes/user_info.py). Without this step the gate exists and nothing asks
   for it.

---

## 6. When to request NDP support

Open a request with NDP support when you need something that is not a
plain grant of an existing tier:

- A new permission level that the Endpoint must enforce (Scenario B).
- An Endpoint whose client has no gates, or whose `AUTHZ_CLIENT_ID` is
  not its own client (the installer warns about both).
- Realm-level changes you do not have admin rights for.

For everything else — granting viewer/writer/admin to a user, listing
members — use the Access Requests screen or the AAI API directly.
