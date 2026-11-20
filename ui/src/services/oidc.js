/**
 * OpenID Connect (Authorization Code) sign-in against the identity provider
 * realm.
 *
 * This is an additional way into the UI, alongside the access-token and
 * username/password forms. It exists because users who authenticate through
 * a federated provider configured in the realm (CILogon, EarthScope, ORCID)
 * have no password in the realm itself, so the credentials form cannot work
 * for them and pasting a token by hand is their only alternative.
 *
 * It signs in with the Endpoint's own confidential client
 * (OIDC_SERVICE_CLIENT_ID), whose secret stays on the server: the browser
 * brings the code back and the API redeems it (POST /user/oidc/token). PKCE
 * is added whenever the browser can compute it (https, localhost); over plain
 * http the sign-in goes without it.
 *
 * The flow ends by handing the resulting access token to
 * ``authAPI.setAndValidateToken``, so validation, storage and the
 * access-denied (403) handling are identical to the other sign-in methods.
 */

import { authAPI, BASE_URL } from './api';

const STORAGE_VERIFIER = 'oidcCodeVerifier';
const STORAGE_STATE = 'oidcState';
const STORAGE_REAUTH = 'oidcReauth';
const CALLBACK_PATH = '/ui/auth/callback';

/**
 * Parse a boolean environment value. Values arrive as strings from the
 * container environment, so the Python-style ``True`` used elsewhere in
 * ``.env`` is accepted alongside the usual spellings.
 *
 * @param {string} value
 * @returns {boolean}
 */
const parseBoolean = (value) =>
  ['true', '1', 'yes', 'on'].includes(String(value ?? '').trim().toLowerCase());

/**
 * Read the OIDC settings injected at container start into config.js.
 *
 * The issuer is the realm URL (KEYCLOAK_URL and AUTHZ_REALM), and the
 * wording is deployment-supplied so it can describe whichever providers that
 * realm actually offers.
 *
 * @returns {{enabled: boolean, issuer: string, clientId: string,
 *            redirectUri: string, scope: string, buttonLabel: string,
 *            helpText: string}}
 */
const getConfig = () => ({
  enabled: parseBoolean(window.__EP_CONFIG__?.oidcEnabled),
  issuer: (window.__EP_CONFIG__?.oidcIssuer ?? '').trim().replace(/\/+$/, ''),
  clientId: (window.__EP_CONFIG__?.oidcClientId ?? '').trim(),
  redirectUri: (window.__EP_CONFIG__?.oidcRedirectUri ?? '').trim(),
  scope: (window.__EP_CONFIG__?.oidcScope ?? '').trim() || 'openid profile email',
  buttonLabel:
    (window.__EP_CONFIG__?.oidcButtonLabel ?? '').trim() ||
    'Sign in with your identity provider',
  helpText: (window.__EP_CONFIG__?.oidcHelpText ?? '').trim(),
});

/**
 * Whether the deployment offers identity-provider sign-in.
 *
 * Off unless OIDC_ENABLED is switched on *and* the client, its realm and
 * OIDC_REDIRECT_URI (the only redirect URI the API redeems codes for) are
 * present, so a half-configured deployment shows nothing rather than a button
 * that fails on click.
 *
 * @returns {boolean}
 */
export const isOidcEnabled = () => {
  const { enabled, issuer, clientId, redirectUri } = getConfig();
  return Boolean(enabled && issuer && clientId && redirectUri);
};

/**
 * Deployment-supplied wording for the button and the line under it. The help
 * text is empty by default: only the deployment knows which providers its
 * realm offers.
 *
 * @returns {{buttonLabel: string, helpText: string}}
 */
export const getOidcLabels = () => {
  const { buttonLabel, helpText } = getConfig();
  return { buttonLabel, helpText };
};

/**
 * Whether the browser can compute a PKCE challenge: ``crypto.subtle`` is only
 * exposed in secure contexts (https, localhost).
 *
 * Without it the sign-in goes without PKCE. A code that leaked could then be
 * redeemed by whoever holds it, until the UI redeems it (at once) or it
 * expires; over plain http the token itself crosses the network unencrypted
 * anyway, as passwords and pasted tokens do.
 *
 * @returns {boolean}
 */
const canDoPkce = () => Boolean(window.isSecureContext && window.crypto?.subtle);

/**
 * Base64url-encode bytes without padding, as required for PKCE.
 *
 * @param {ArrayBuffer|Uint8Array} buffer
 * @returns {string}
 */
const base64UrlEncode = (buffer) => {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  let binary = '';
  bytes.forEach((b) => {
    binary += String.fromCharCode(b);
  });
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
};

/**
 * Generate a high-entropy random string suitable for a code verifier or state.
 *
 * @param {number} byteLength
 * @returns {string}
 */
const randomString = (byteLength = 32) =>
  base64UrlEncode(window.crypto.getRandomValues(new Uint8Array(byteLength)));

/**
 * Derive the S256 code challenge from a verifier.
 *
 * @param {string} verifier
 * @returns {Promise<string>}
 */
const deriveChallenge = async (verifier) => {
  const digest = await window.crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(verifier)
  );
  return base64UrlEncode(digest);
};

/**
 * Note that the user signed out of this Endpoint, as the AAI console does: the
 * identity provider's session stays (other NDP sites stay signed in), but the
 * next sign-in here asks for credentials (prompt=login) instead of coming
 * straight back as the same user.
 */
export const markSignedOut = () => {
  localStorage.setItem(STORAGE_REAUTH, '1');
};

/**
 * Start the sign-in: remember the state and, when the browser can, a PKCE
 * verifier, and send the browser to the realm's login page — where the
 * federated providers configured on the realm are offered.
 *
 * @returns {Promise<void>} Resolves as the browser navigates away.
 */
export const beginOidcLogin = async () => {
  if (!isOidcEnabled()) {
    throw new Error('No identity provider is configured for this Endpoint.');
  }

  const { issuer, clientId, redirectUri, scope } = getConfig();
  const state = randomString(16);

  // sessionStorage, not localStorage: the state and verifier are single-use
  // and must not outlive the tab or leak into other sessions.
  sessionStorage.setItem(STORAGE_STATE, state);

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: clientId,
    redirect_uri: redirectUri,
    scope,
    state,
  });
  if (localStorage.getItem(STORAGE_REAUTH)) {
    params.set('prompt', 'login');
  }

  // Over plain http the browser cannot compute PKCE (see canDoPkce).
  if (canDoPkce()) {
    const verifier = randomString();
    sessionStorage.setItem(STORAGE_VERIFIER, verifier);
    params.set('code_challenge', await deriveChallenge(verifier));
    params.set('code_challenge_method', 'S256');
  } else {
    sessionStorage.removeItem(STORAGE_VERIFIER);
  }

  // The realm's login page: Keycloak's authorization endpoint, as the API
  // uses its token endpoint (keycloak_token_url).
  window.location.assign(
    `${issuer}/protocol/openid-connect/auth?${params.toString()}`
  );
};

/**
 * Whether the current URL is the identity provider redirecting back to us.
 * OIDC_REDIRECT_URI must end in CALLBACK_PATH: no other path is recognized.
 *
 * @returns {boolean}
 */
export const isOidcCallback = () => {
  if (!window.location.pathname.endsWith(CALLBACK_PATH)) {
    return false;
  }
  const params = new URLSearchParams(window.location.search);
  return params.has('code') || params.has('error');
};

/**
 * Remove the authorization code from the address bar and return the user to
 * the UI root, so a reload cannot replay a spent code.
 */
const clearCallbackUrl = () => {
  window.history.replaceState({}, document.title, `${BASE_URL}/ui/`);
};

/**
 * Have the API redeem the code with the client's secret, which the browser
 * never sees.
 *
 * @param {string} code
 * @param {string|null} verifier null when signed in without PKCE.
 * @returns {Promise<Response>}
 */
const redeemCode = (code, verifier) =>
  fetch(`${BASE_URL}/user/oidc/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(verifier ? { code, code_verifier: verifier } : { code }),
  });

/**
 * Complete the sign-in: exchange the authorization code for tokens, then hand
 * the access token to the shared validation path.
 *
 * @returns {Promise<Object>} User information, once validated by the API.
 */
export const completeOidcLogin = async () => {
  const params = new URLSearchParams(window.location.search);
  const storedState = sessionStorage.getItem(STORAGE_STATE);
  const verifier = sessionStorage.getItem(STORAGE_VERIFIER);

  sessionStorage.removeItem(STORAGE_STATE);
  sessionStorage.removeItem(STORAGE_VERIFIER);

  // The provider reported a failure (for example the user cancelled).
  if (params.has('error')) {
    clearCallbackUrl();
    throw new Error(
      params.get('error_description') ||
        `Sign-in was not completed (${params.get('error')}).`
    );
  }

  const code = params.get('code');
  const returnedState = params.get('state');

  if (!storedState || returnedState !== storedState) {
    clearCallbackUrl();
    throw new Error(
      'Sign-in could not be verified. Please try again.'
    );
  }

  let data = {};
  let ok = false;
  try {
    const response = await redeemCode(code, verifier);
    data = await response.json().catch(() => ({}));
    ok = response.ok;
  } catch (error) {
    clearCallbackUrl();
    throw error;
  }

  if (!ok || !data.access_token) {
    clearCallbackUrl();
    throw new Error(
      (typeof data.detail === 'string' && data.detail) ||
        'The identity provider did not issue a token.'
    );
  }

  // Reuse the shared path so an Endpoint-level denial (403) surfaces exactly
  // as it does for the other sign-in methods, carrying `deniedToken` so the
  // access-request flow can be offered.
  try {
    const userInfo = await authAPI.setAndValidateToken(data.access_token);
    clearCallbackUrl();
    localStorage.removeItem(STORAGE_REAUTH);
    return userInfo;
  } catch (error) {
    clearCallbackUrl();

    // A 403 is a real authorization decision: keep it as-is so the caller can
    // offer the access-request form. Signing in again then asks for
    // credentials, so the user can pick another account.
    if (error.deniedToken) {
      markSignedOut();
      throw error;
    }

    // Anything else happened *after* the provider already authenticated the
    // user, so the shared "Invalid token" wording would wrongly suggest they
    // mistyped their credentials. Say what actually failed instead.
    const failure = new Error(
      'You signed in successfully, but this Endpoint could not validate the ' +
        'resulting token. This is a configuration problem on the Endpoint, ' +
        'not a problem with your credentials. ' +
        `(${error.message || 'unknown error'})`
    );
    failure.cause = error;
    throw failure;
  }
};
