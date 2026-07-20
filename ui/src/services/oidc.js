/**
 * OpenID Connect (Authorization Code + PKCE) sign-in against the identity
 * provider realm.
 *
 * This is an additional way into the UI, alongside the access-token and
 * username/password forms. It exists because users who authenticate through
 * a federated provider configured in the realm (CILogon, EarthScope, ORCID)
 * have no password in the realm itself, so the credentials form cannot work
 * for them and pasting a token by hand is their only alternative.
 *
 * A public client with PKCE is used rather than a confidential one so that no
 * client secret has to be distributed with the Endpoint, which is self-hosted
 * by many institutions.
 *
 * The flow ends by handing the resulting access token to
 * ``authAPI.setAndValidateToken``, so validation, storage and the
 * access-denied (403) handling are identical to the other sign-in methods.
 */

import { authAPI, BASE_URL } from './api';

const STORAGE_VERIFIER = 'oidcCodeVerifier';
const STORAGE_STATE = 'oidcState';
const CALLBACK_PATH = '/ui/auth/callback';

/**
 * Read the OIDC settings injected at container start into config.js.
 *
 * @returns {{issuer: string, clientId: string, scope: string}}
 */
const getConfig = () => ({
  issuer: (window.__EP_CONFIG__?.oidcIssuer ?? '').trim().replace(/\/+$/, ''),
  clientId: (window.__EP_CONFIG__?.oidcClientId ?? '').trim(),
  scope: (window.__EP_CONFIG__?.oidcScope ?? '').trim() || 'openid profile email',
});

/**
 * Whether the deployment has configured an identity provider. Deployments that
 * leave OIDC_ISSUER or OIDC_CLIENT_ID empty keep the previous behaviour and
 * never see the button.
 *
 * @returns {boolean}
 */
export const isOidcEnabled = () => {
  const { issuer, clientId } = getConfig();
  return Boolean(issuer && clientId);
};

/**
 * Whether the browser can perform PKCE.
 *
 * ``crypto.subtle`` is only exposed in secure contexts, so a deployment served
 * over plain http on a bare IP cannot compute an S256 challenge. Rather than
 * silently downgrading to the ``plain`` challenge method, the button is
 * disabled and the reason is shown — the other two sign-in methods still work.
 *
 * @returns {boolean}
 */
export const isOidcSupported = () =>
  Boolean(window.isSecureContext && window.crypto?.subtle);

/**
 * The redirect URI this deployment will use. It must be registered on the
 * client in the realm, so it is also surfaced in the UI to make configuration
 * mistakes diagnosable.
 *
 * @returns {string}
 */
export const getRedirectUri = () =>
  `${window.location.origin}${BASE_URL}${CALLBACK_PATH}`;

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
 * Fetch the realm's discovery document so the endpoints do not have to be
 * hardcoded to a particular identity provider's URL layout.
 *
 * @returns {Promise<Object>}
 */
const discover = async () => {
  const { issuer } = getConfig();
  const response = await fetch(`${issuer}/.well-known/openid-configuration`);

  if (!response.ok) {
    throw new Error(
      `Could not reach the identity provider (HTTP ${response.status}). ` +
        'Check that OIDC_ISSUER is correct.'
    );
  }

  return response.json();
};

/**
 * Start the sign-in: build a PKCE challenge, remember the verifier and state,
 * and send the browser to the realm's login page — where the federated
 * providers configured on the realm are offered.
 *
 * @returns {Promise<void>} Resolves as the browser navigates away.
 */
export const beginOidcLogin = async () => {
  if (!isOidcEnabled()) {
    throw new Error('No identity provider is configured for this Endpoint.');
  }
  if (!isOidcSupported()) {
    throw new Error(
      'Signing in through the identity provider requires a secure (https) ' +
        'connection. Use an access token or your username and password instead.'
    );
  }

  const { clientId, scope } = getConfig();
  const config = await discover();

  const verifier = randomString();
  const state = randomString(16);

  // sessionStorage, not localStorage: the verifier is single-use and must not
  // outlive the tab or leak into other sessions.
  sessionStorage.setItem(STORAGE_VERIFIER, verifier);
  sessionStorage.setItem(STORAGE_STATE, state);

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: clientId,
    redirect_uri: getRedirectUri(),
    scope,
    state,
    code_challenge: await deriveChallenge(verifier),
    code_challenge_method: 'S256',
  });

  window.location.assign(`${config.authorization_endpoint}?${params.toString()}`);
};

/**
 * Whether the current URL is the identity provider redirecting back to us.
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
  if (!verifier) {
    clearCallbackUrl();
    throw new Error('Sign-in session has expired. Please try again.');
  }

  const { clientId } = getConfig();
  const config = await discover();

  const response = await fetch(config.token_endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: clientId,
      code,
      redirect_uri: getRedirectUri(),
      code_verifier: verifier,
    }).toString(),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok || !data.access_token) {
    clearCallbackUrl();
    throw new Error(
      data.error_description ||
        data.error ||
        'The identity provider did not issue a token.'
    );
  }

  // Reuse the shared path so an Endpoint-level denial (403) surfaces exactly
  // as it does for the other sign-in methods, carrying `deniedToken` so the
  // access-request flow can be offered.
  try {
    const userInfo = await authAPI.setAndValidateToken(data.access_token);
    clearCallbackUrl();
    return userInfo;
  } catch (error) {
    clearCallbackUrl();
    throw error;
  }
};
