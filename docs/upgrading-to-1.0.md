# Upgrading to 1.0.0

**Summary.** 1.0.0 moves permissions to Keycloak: each guarded route asks Keycloak whether the caller passes a gate of the Endpoint's own client. An Endpoint whose client has no gates yet (every client created by Federation 1.x) keeps deciding from roles as before, so upgrading does not lock anyone out. To upgrade, run the installer again; check the four points under [After upgrading](#after-upgrading).

What changes is listed in the [CHANGELOG](../CHANGELOG.md) under 1.0.0. How permissions are decided is in [roles-and-permissions.md](roles-and-permissions.md).

## Upgrade

**With the installer** (recommended). Run it again, as for any release (see [operations.md](operations.md#upgrading)). It writes the new settings from the Federation registration:

| Setting | Value |
| ------- | ----- |
| `KEYCLOAK_URL` | the identity provider's host, replacing `AUTH_API_URL` |
| `OIDC_SERVICE_CLIENT_ID` | the Endpoint's client, `ep-<config-id>` |
| `OIDC_SERVICE_CLIENT_SECRET` | that client's secret, when the Federation provides it |
| `AUTHZ_REALM` | the realm, `NDP` by default |

**By hand.** Move the checkout to `v1.0.0` and edit `.env`:

- `KEYCLOAK_URL`: the host of `AUTH_API_URL` (e.g. `https://idp.nationaldataplatform.org`). If it is missing, `AUTH_API_URL` is still read and its host kept.
- `OIDC_SERVICE_CLIENT_ID=ep-<config-id>`. If it is missing, an entry `ndp_ep/ep-<config-id>` in `GROUP_NAMES` gives it, with a warning in the log.
- `AUTHZ_CLIENT_ID` and `ENABLE_GROUP_BASED_ACCESS` are no longer read; they can be removed.

Then rebuild: `docker compose ... up -d --build`.

## Who can do what

It depends on whether the Endpoint's Keycloak client has the gates (`admin-area`, `editor-area`, `viewer-area`). Clients created by Federation 2.0.0 or later have them; older ones get them when adopted with the AAI's `tools/adopt_client.py`, run by the platform team.

| | Client without gates (Federation 1.x) | Client with gates |
| - | - | - |
| How it is decided | from the user's roles, as before 1.0.0 | by Keycloak, from the user's level in `ndp_ep/ep-<config-id>` |
| Log | `has no permission gates`, once | nothing |
| Realm roles such as `ndp_writer` | still count | no longer count: the user needs the editor or admin level in the group |

Nothing has to be done on the Endpoint when its client is adopted: the next request is decided by the gates.

**Writing to S3** (creating and deleting buckets, uploading, deleting objects) now needs the admin tier on both kinds of client. Editors can still list and download.

## Access requests

Approving a request adds the user to `ndp_ep/<OIDC_SERVICE_CLIENT_ID>` at the requested level with one AAI call. With `OIDC_SERVICE_CLIENT_SECRET` the Endpoint's client vouches for the call; without it the call goes without that proof, which the AAI in production accepts for now. When the AAI starts checking the calling app, an Endpoint without the secret has to re-run the installer.

## After upgrading

1. `GET /status/` reports `keycloak_url` with the identity provider's host.
2. Signing in to the UI works, and `GET /user/info` returns your `effective_role` (`admin`, `writer` or `viewer`).
3. The log says either nothing about gates (the client has them) or `has no permission gates` once (decided from roles; expected until the client is adopted).
4. An editor can create a dataset; only an admin can upload to S3.

If everyone gets 403, check that `OIDC_SERVICE_CLIENT_ID` (or `GROUP_NAMES`) is set and names the Endpoint's own client.

The compatibility code that keeps clients without gates working is listed, with when it can be removed, in [compatibility-shims.md](compatibility-shims.md).
