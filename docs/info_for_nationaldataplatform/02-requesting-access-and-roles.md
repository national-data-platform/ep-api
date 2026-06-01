# Requesting access and the role tiers

To **publish** or **modify** data on an Endpoint you need a role. Roles are
**per-Endpoint** (you may be a writer on one Endpoint and a viewer on another)
and they live in the central identity service, so they travel inside your NDP
login. You do not maintain a separate password per Endpoint.

## The three role tiers

| Role | Can do |
|---|---|
| 👁️ **Viewer** | View and search the catalog (including public data anyone can see). Read-only. |
| ✏️ **Writer** | Everything a viewer does, **plus** create / edit / delete organizations, datasets, services and resources; use the **S3 Management** tool. |
| 🛠️ **Admin** | Everything a writer does, **plus** review access requests and reach admin-only pages (dashboard, settings). |

The tiers are **hierarchical**: an admin does not also need a writer role
assigned; a writer does not also need a viewer role assigned. You only need the
**highest tier you want**.

**Without a role**, an authenticated user can still search and read public data
on the Endpoint, but cannot create or modify anything — this is the secure
default.

## Requesting access

If you sign in and the Endpoint denies a write action — or if you simply want to
contribute — request access from the Endpoint itself:

1. Sign in with your NDP (CI Logon) account at your institution's Endpoint URL.
2. If you have no role yet, the Endpoint shows a **Request access** form with a
   short **justification** field — describe what you want to do and which group
   or project you belong to.
3. Submit. The request now appears as **pending** to the Endpoint's
   administrators.

## What the administrator does

An Endpoint administrator opens the **Access Requests** page, reviews pending
requests and either **approves** the request with a tier — **Viewer**, **Writer**
or **Admin** — or **rejects** it with a brief reason.

Approving grants the role to your account on this Endpoint.

## After approval

The new role takes effect when your **next token is issued** — typically on
your next sign-in. If the Endpoint still acts as if you had no role, sign out
and back in to refresh.

If your role is removed or changed later, the same applies: the change is
visible after the next sign-in.

## Once you have a writer role

You can publish through the **`+ New`** menu and manage your data on the
**Search** page. See [Publishing data](03-publishing-data.md) for the available
flows and the fields each one requires.
