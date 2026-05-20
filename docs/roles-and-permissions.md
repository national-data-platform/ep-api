# Roles and permissions

This document explains the role model the Endpoint (EP) enforces, how a
user's roles travel from Keycloak into the JWT, and the exact steps to
grant access or introduce a new role. It is aimed at deployment
operators and at NDP support.

> TL;DR
> - The EP understands three tiers: **viewer** (read), **writer**
>   (modify catalog content) and **admin** (everything).
> - Roles are Keycloak **realm roles** named either `ndp_{tier}`
>   (platform-wide) or `group:{AFFINITIES_EP_UUID}:{tier}` (per-EP).
> - Assigning an existing tier to a user is **configuration only** (AAI
>   API or the Access Requests screen). A genuinely new permission level
>   requires an **Endpoint code change** (see
>   [Scenario B](#scenario-b-a-brand-new-permission-level)).

---

## 1. The three tiers

| Tier   | Can do | Implied lower tiers |
| ------ | ------ | ------------------- |
| viewer | Read / browse only (Search, view details). | — |
| writer | Everything a viewer can, plus create / edit / delete / publish catalog content. | viewer |
| admin  | Everything a writer can, plus manage access requests and admin-only pages. | writer, viewer |

The tiers are hierarchical: an **admin** does not also need the writer
and viewer roles, and a **writer** does not also need viewer. The
Endpoint resolves the highest tier the user holds.

**Strict default:** a user who is a member of the EP group but holds
**no** recognised role is treated as `none` and cannot perform any write
operation. They can still authenticate and read.

---

## 2. Role naming convention

Every recognised role is a Keycloak **realm role**. Two forms are
accepted for each tier:

| Tier   | Platform-wide (any EP) | Per-endpoint                                |
| ------ | ---------------------- | ------------------------------------------- |
| admin  | `ndp_admin`            | `group:{AFFINITIES_EP_UUID}:admin`          |
| writer | `ndp_writer`           | `group:{AFFINITIES_EP_UUID}:writer`         |
| viewer | `ndp_viewer`           | `group:{AFFINITIES_EP_UUID}:viewer`         |

`{AFFINITIES_EP_UUID}` is the value of the `AFFINITIES_EP_UUID`
environment variable for this deployment (it is also the name of the
endpoint's Keycloak group). Example for the dev EP whose UUID is
`96207a63-ee21-40c8-a492-31d680002330`:

```
group:96207a63-ee21-40c8-a492-31d680002330:writer
```

The legacy per-EP admin form `{AFFINITIES_EP_UUID}_admin` (no `group:`
prefix, underscore before `admin`) is **also** still accepted for admin,
for backwards compatibility. New deployments should prefer the
`group:{uuid}:admin` form.

> **Gotcha — "editor" vs "writer".** The AAI's own group model uses the
> default role names `admin` / `editor` / `viewer`. The Endpoint, by
> contrast, recognises `admin` / `writer` / `viewer`. Assigning the
> AAI's `editor` role does **not** grant write access on the EP — you
> must assign `writer`. Only `admin`, `writer` and `viewer` are mapped
> to EP permissions.

---

## 3. How the Endpoint sees roles

When a user authenticates, the AAI returns their realm roles in the
`roles` claim. `GET /user/info` exposes them, plus a derived
`effective_role` field that is the single value the UI and API gating
rely on:

```jsonc
GET /user/info
{
  "username": "raul",
  "sub": "6bfaa6c3-…",
  "roles": ["ndp_admin", "group:96207a63-…:admin", "default-roles-ndp"],
  "effective_role": "admin"      // admin | writer | viewer | none
}
```

The matching logic lives in
[`api/services/auth_services/authorization_service.py`](../api/services/auth_services/authorization_service.py):

- `is_admin`, `is_writer`, `is_viewer` — tier checks (each implies the
  lower tiers).
- `effective_role` — returns the highest tier as a string.
- `get_user_for_write_operation` — the FastAPI dependency guarding every
  `POST`/`PUT`/`PATCH`/`DELETE`; rejects callers below writer with `403`.
- `get_user_for_read_operation` — viewer-or-above dependency, available
  for future read endpoints.

Any realm role that does not match one of the six names in the table
above is carried in the token but **ignored** by the EP for permission
purposes (it will not raise `effective_role` above what the recognised
roles grant).

---

## 4. How roles reach the JWT (the "Keycloak client" question)

Roles are emitted into the token by a **protocol mapper** on the
Keycloak client (`oidc-usermodel-realm-role-mapper`, claim name
`roles`). This mapper is configured once, when the client is created by
the AAI (see `create_client` in the AAI's
`services/direct_keycloak/client_service.py`).

**You do not need to touch the Keycloak client when you add a new realm
role.** Because the mapper emits the user's realm roles wholesale, a
newly created `group:{uuid}:…` role appears in the token as soon as it
is assigned — no per-role client change, no client-scope edit.

This was verified empirically: creating a brand-new realm role
`group:{uuid}:probe-doc`, assigning it to a user, and re-reading
`GET /user/info` showed the role present in `roles` immediately, with no
client modification. (`effective_role` stayed `viewer` because
`probe-doc` is not a recognised tier — see
[Scenario B](#scenario-b-a-brand-new-permission-level).)

The only situation where the client *would* matter is a deployment whose
client was created **without** the realm-roles mapper, or one relying on
client-specific roles (`resource_access.{client}.roles`) instead of
realm roles. The standard AAI-provisioned client already includes the
mapper, so this is not a concern for normal deployments.

---

## 5. AAI API for role and group management

The AAI API (base URL = `AUTH_API_URL` host) is authoritative for group
and role writes; it wraps the Keycloak Admin API and enforces that the
caller is a group admin/editor. All calls take the caller's own Bearer
token.

| Action | Endpoint | Body | Notes |
| ------ | -------- | ---- | ----- |
| Create a custom role in a group | `POST /role/create` | `{groupName, roleName, users?:[]}` | `roleName` is the bare tier (e.g. `writer`); the AAI builds `group:{groupName}:{roleName}`. The names `admin`/`editor`/`viewer` are reserved and cannot be created. Caller must be group editor. |
| Assign a role to user(s) | `POST /role/assign` | `{groupName, roleName, username \| users:[]}` | `roleName` is the **bare** tier — do **not** pass the fully-qualified `group:…:writer` string (it double-prefixes). Assigning `admin` requires the caller to be a group admin. |
| Remove a role from user(s) | `DELETE /role/remove` | `{groupName, roleName, username \| users:[]}` | |
| Delete a custom role | `DELETE /role/delete` | `{groupName, roleName}` | Cannot delete `admin`/`editor`/`viewer`. Caller must be group admin. |
| Add user to a group | `POST /group/add-user` | `{group_name, username}` | The AAI assigns the `viewer` role automatically on join. |
| List group members | `GET /group/members?group_name=…` | — | |

The Endpoint's own thin wrapper around these lives in
[`api/services/auth_services/aai_client.py`](../api/services/auth_services/aai_client.py)
(`assign_role`, `add_user_to_group`, `list_group_members`).

---

## 6. Common tasks

### Grant an existing tier to a user

**Via the UI (preferred).** When a user requests access, an admin
approves the request on the **Access Requests** page and picks the tier
(Viewer / Writer / Admin). This adds the user to the EP group and
assigns the chosen per-EP role.

**Via the AAI API.** Add the user to the group (this gives them
`viewer`), then assign a higher tier if needed:

```bash
TOKEN=$(curl -s -X POST "$AAI/user/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"<admin>","password":"<pass>"}' | jq -r .access_token)

# join the group (auto-assigns viewer)
curl -s -X POST "$AAI/group/add-user" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"group_name":"<EP_UUID>","username":"<user>"}'

# upgrade to writer (bare tier name + groupName)
curl -s -X POST "$AAI/role/assign" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"groupName":"<EP_UUID>","roleName":"writer","username":"<user>"}'
```

The user must **re-login** afterwards: their old JWT was issued before
the grant and will not contain the new role until a fresh token is
minted.

### Scenario A: reuse an existing tier in another group

Nothing in the Endpoint changes. Create/assign the
`group:{OTHER_UUID}:viewer|writer|admin` roles for that group. The
Endpoint only ever evaluates roles for **its own** `AFFINITIES_EP_UUID`,
so per-group roles for other endpoints are naturally isolated.

### Scenario B: a brand-new permission level

If you need a tier that is **not** viewer/writer/admin (say, a
`publisher` that can publish but not delete), two things are required:

1. **Create the role** in Keycloak / via the AAI as usual
   (`group:{uuid}:publisher`). It will appear in the token automatically
   (Section 4).
2. **Teach the Endpoint about it** — a code change in
   [`authorization_service.py`](../api/services/auth_services/authorization_service.py):
   add a matcher (e.g. `is_publisher`), fold it into `effective_role`,
   and gate the relevant routes/dependencies. Without this step the role
   rides in the token but grants nothing (`effective_role` ignores it).

Step 2 is the part that "request to NDP support" covers when an operator
cannot change the Endpoint code themselves.

---

## 7. When to request NDP support

Open a request with NDP support when you need something that is not a
plain assignment of an existing tier:

- A new permission level that the Endpoint must enforce (Scenario B).
- Changes to the Keycloak client itself (new protocol mappers, switching
  to client roles) — only relevant for non-standard clients (Section 4).
- Realm-level changes you do not have admin rights for.

For everything else — granting viewer/writer/admin to a user, creating a
per-group custom role, listing members — use the Access Requests screen
or the AAI API directly.
