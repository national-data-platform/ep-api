# Signing in through NDP

The optional "Sign in through NDP" button on the login screen, for users who
come through CILogon, ORCID and the other providers of the NDP realm and have
no password to type. It signs in with the Endpoint's own client,
`OIDC_SERVICE_CLIENT_ID`; its secret stays on the server.

Drawn against an Endpoint with `OIDC_ENABLED=True`, `OIDC_REDIRECT_URI` set and
the client's id and secret in `.env`. The settings are in
[../configuration.md](../configuration.md#identity-provider-sign-in-optional-off-by-default).

## The sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Endpoint UI (browser)
    participant KC as Keycloak (NDP realm)

    rect rgba(128, 128, 128, 0.08)
    Note over User,KC: On the NDP login page
    User->>UI: click "Sign in through NDP"
    Note over UI: saves a random state<br/>(and a PKCE verifier on https)
    UI->>KC: open the NDP login page<br/>with the client id, OIDC_REDIRECT_URI and state
    opt skipped if the user already has a signed-in NDP session
        User->>KC: choose CILogon
        create participant CI as CILogon
        KC->>CI: send the browser to CILogon
        User->>CI: sign in with their institution
        CI-->>KC: send the browser back with a code
        KC->>CI: trade the code for the user's identity,<br/>with Keycloak's own CILogon client
        destroy CI
        CI-->>KC: name, email, …
        Note over KC: the same kind of exchange, one level up:<br/>CILogon's tokens stay in Keycloak
    end
    KC-->>UI: redirect to OIDC_REDIRECT_URI?code=…&state=…
    Note over KC,UI: Keycloak only redirects the browser:<br/>it never connects to the Endpoint
    end

    %% Declared after CILogon, so that it sits next to Keycloak.
    participant EP as Endpoint API
    participant AAI as AAI API

    rect rgba(70, 110, 180, 0.1)
    Note over UI,EP: Trading the code for a token
    Note over UI: checks the state matches the saved one
    UI->>EP: POST {ep-api}/user/oidc/token on the Endpoint API<br/>body: {code, code_verifier when PKCE}
    EP->>KC: POST {keycloak-url}/protocol/openid-connect/token<br/><br/>body: the code, the client id and secret, redirect_uri = OIDC_REDIRECT_URI
    KC-->>EP: access, refresh and id tokens
    EP-->>UI: the access token only
    end

    rect rgba(128, 128, 128, 0.08)
    Note over UI,AAI: Entering, as with a pasted token
    UI->>EP: GET {ep-api}/user/info + Bearer access token
    EP->>AAI: POST /information {"token": …}: who is this?
    AAI-->>EP: sub, username, groups, roles
    EP->>KC: does the user pass admin-area,<br/>then editor-area, then viewer-area?
    KC-->>EP: the first gate passed, or none
    alt a gate passed
        EP-->>UI: user info + effective_role
        Note over UI: keeps the token and opens the UI
    else none
        EP-->>UI: 403
        Note over UI: offers the access-request form
    end
    end
```

## Worth knowing

**Only the browser has to reach the Endpoint.** Keycloak sends the browser to
`OIDC_REDIRECT_URI`; it never connects to it. An Endpoint on a private address,
reached over a VPN, signs in the same way.

**The callback address is pinned.** The clients the Federation creates accept
any redirect URI. The API redeems codes for `OIDC_REDIRECT_URI` only, so a code
sent anywhere else cannot be redeemed with this Endpoint's secret. It must end
in `<ROOT_PATH>/ui/auth/callback`: the UI recognizes no other path as the
return from the login page, and the sign-in then ends quietly back on the login
card.

**Over plain http there is no PKCE.** Browsers compute it only on https and
`localhost`. A code that leaked on the way could then be redeemed by whoever
holds it, until the UI redeems it (at once) or it expires (one use, about a
minute). The access token crosses the network unencrypted anyway, as passwords
and pasted tokens do.

**Signing out leaves the NDP session open.** Other NDP sites stay signed in.
The next sign-in here sends `prompt=login`, so Keycloak shows its login form
instead of signing the same user straight back in. A 403 does the same, so the
user can try another account.
