# Requesting access and the role tiers

Two things decide what you can do on an Endpoint:

- **Entry.** On an Endpoint registered with the NDP Federation, you must be a
  member of the Endpoint's group (`ndp_ep/ep-<config-id>`) to get in at all,
  unless you hold the platform-wide `ndp_admin` role. A standalone Endpoint
  lets in anyone the NDP authentication service accepts.
- **Role.** Once in, your role decides whether you can only look, or also
  create and change things.

Groups and roles live in the NDP authentication service and travel inside your
NDP token. You do not keep a separate account per Endpoint.

## The three role tiers

| Role | Can do |
|---|---|
| 👁️ **Viewer** | Search and browse. Read-only. |
| ✏️ **Writer** | Everything a viewer does, **plus** create, edit and delete organizations, datasets, services and resources, send datasets to the staging catalog, and use the **S3 storage** page. |
| 🛠️ **Admin** | Everything a writer does, **plus** the admin-only pages: **Dashboard** and, when access requests are enabled, **Access Requests**. |

The tiers are **hierarchical**: an admin does not also need a writer role
assigned; a writer does not also need a viewer role assigned. You only need the
**highest tier you want**.

A role can be given for one Endpoint — `group:<endpoint group>:<tier>`, for
example `group:ndp_ep/ep-<config-id>:writer` — or platform-wide (`ndp_viewer`,
`ndp_writer`, `ndp_admin`). The identity provider calls the write tier
**editor**; the Endpoint treats `editor` and `writer` as the same tier.

**Without a role**, a user who got in can search and browse but cannot create
or modify anything.

## Requesting access

The request form appears when the Endpoint **refuses you at sign-in** — that
is, on a registered Endpoint whose group you are not in:

1. Sign in at the Endpoint's address (`<endpoint-url>/ui/`).
2. The Endpoint says you do not have permission to access it, and offers
   **Request access to this Endpoint**, with a short **justification** field —
   describe what you want to do and which group or project you belong to.
3. Submit. The request appears as **pending** to the Endpoint's
   administrators. If you already have a pending request, you are told so.

This works only on an Endpoint whose operator enabled access requests
(`ENABLE_ACCESS_REQUESTS=True`, which also needs a MongoDB; the installer
provides one when you answer yes to *Enable access requests?*). Otherwise the
form answers that access requests are disabled, and access has to be arranged
with the Endpoint's administrator directly.

A user who can already enter but has no role does not see the form; a role
is then given by an administrator outside the Endpoint.

## What the administrator does

An Endpoint administrator opens the **Access Requests** page, reviews pending
requests and either **approves** the request as **Viewer**, **Writer** or
**Admin** (Viewer is preselected), or **rejects** it, optionally with notes.

Approving makes the change in the NDP authentication service with the
administrator's own token: it adds you to the Endpoint's group and, for Writer
or Admin, assigns that role on the group. Since Endpoint version 0.34.46 the
group is the Endpoint's own Federation group, the first entry of its
`GROUP_NAMES` setting. An Endpoint with no group configured — a standalone
one — cannot approve requests. If the authentication service refuses the
change, the request stays pending and the administrator can try again.

Rejecting only records the decision.

## After approval

The new group and role take effect when your **next token is issued** —
typically on your next sign-in. If the Endpoint still refuses you or acts as
if you had no role, sign out, get a fresh token and sign in again.

The same applies if your role is removed or changed later.

## Once you have a writer role

The **`+ New`** menu appears in the navigation bar, and your own items on the
**Search** page offer **Delete** and, for datasets, **Publish**. See
[Publishing data](03-publishing-data.md) for the available flows and the fields
each one requires.
