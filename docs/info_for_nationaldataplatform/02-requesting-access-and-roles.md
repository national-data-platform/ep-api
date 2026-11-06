# Requesting access and the role tiers

What you can do on an Endpoint comes from your **level in the Endpoint's
group** (`ndp_ep/ep-<config-id>`) in the NDP identity provider: `viewers`,
`editors` or `admins`. It decides two things:

- **Entry.** On an Endpoint registered with the NDP Federation you need one of
  those levels to get in at all, unless you hold the platform-wide `ndp_admin`
  role. A standalone Endpoint lets in anyone the NDP authentication service
  accepts, but nobody can create or change anything on it.
- **Tier.** Once in, your level decides whether you can only look, or also
  create and change things.

The Endpoint asks the identity provider (Keycloak) about your level on every
request. You do not keep a separate account per Endpoint, and a new level
applies straight away.

## The three tiers

| Tier | Can do |
|---|---|
| 👁️ **Viewer** | Search and browse. Read-only. |
| ✏️ **Writer** | Everything a viewer does, **plus** create, edit and delete organizations, datasets, services and resources, send datasets to the staging catalog, and use the **S3 storage** page. |
| 🛠️ **Admin** | Everything a writer does, **plus** the admin-only pages: **Dashboard** and, when access requests are enabled, **Access Requests**. |

The tiers are **hierarchical**: an admin does not also need to be an editor;
an editor does not also need to be a viewer. You only need the **highest tier
you want**.

A tier is your level in the Endpoint's group: **viewers**, **editors** (the
identity provider's name for writers) or **admins**. A level on a parent
group, such as `ndp_ep`, can count on every Endpoint below it. The only
platform-wide role that counts is `ndp_admin`; realm roles such as
`ndp_writer` or `group:<group>:writer` grant nothing on their own.

**Without a level** you cannot enter a registered Endpoint at all; catalog
searches through the API stay public.

## Requesting access

The request form appears when the Endpoint **refuses you at sign-in** — that
is, on a registered Endpoint where you have no level:

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

A viewer who wants to write does not see the form, since they can already
enter; an administrator raises their level directly, in the identity
provider's group or through its AAI API.

## What the administrator does

An Endpoint administrator opens the **Access Requests** page, reviews pending
requests and either **approves** the request as **Viewer**, **Writer** or
**Admin** (Viewer is preselected), or **rejects** it, optionally with notes.

Approving makes the change in the NDP authentication service with the
administrator's own token: it adds you to the Endpoint's own Federation
group at the level picked (Viewer, Editor for Writer, or Admin). An Endpoint
with no Keycloak client — a standalone one — cannot approve requests. If the
authentication service refuses the change, the request stays pending and the
administrator can try again.

Rejecting only records the decision.

## After approval

The new level applies **straight away**: the Endpoint asks the identity
provider on every request, so you only need to sign in again to get past the
screen that refused you. You do not need a new token.

Taking a level away, or lowering it, can take until your current token
expires to show.

## Once you are a writer

The **`+ New`** menu appears in the navigation bar, and your own items on the
**Search** page offer **Delete** and, for datasets, **Publish**. See
[Publishing data](03-publishing-data.md) for the available flows and the fields
each one requires.
