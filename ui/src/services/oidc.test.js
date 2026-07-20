import {
  isOidcEnabled,
  isOidcSupported,
  isOidcCallback,
  getRedirectUri,
  beginOidcLogin,
} from './oidc';

// ./api reads window.__EP_CONFIG__ and constructs an axios client at import
// time; only BASE_URL and the shared validation entry point matter here.
jest.mock('./api', () => ({
  BASE_URL: '/ep-api',
  authAPI: { setAndValidateToken: jest.fn() },
}));

const setConfig = (config) => {
  window.__EP_CONFIG__ = config;
};

const setUrl = (path) => {
  window.history.replaceState({}, '', path);
};

describe('oidc configuration gate', () => {
  afterEach(() => {
    delete window.__EP_CONFIG__;
  });

  // The central guarantee of this feature: a deployment that does not
  // configure an identity provider must behave exactly as it did before.
  it('is disabled when no configuration is present', () => {
    delete window.__EP_CONFIG__;
    expect(isOidcEnabled()).toBe(false);
  });

  it('is disabled when the configuration is empty', () => {
    setConfig({ oidcIssuer: '', oidcClientId: '' });
    expect(isOidcEnabled()).toBe(false);
  });

  it('is disabled when only the issuer is set', () => {
    setConfig({ oidcIssuer: 'https://idp.example.org/realms/NDP' });
    expect(isOidcEnabled()).toBe(false);
  });

  it('is disabled when only the client id is set', () => {
    setConfig({ oidcClientId: 'ndp-ep-ui' });
    expect(isOidcEnabled()).toBe(false);
  });

  it('is disabled when values are only whitespace', () => {
    setConfig({ oidcIssuer: '   ', oidcClientId: '  ' });
    expect(isOidcEnabled()).toBe(false);
  });

  it('is enabled when both issuer and client id are set', () => {
    setConfig({
      oidcIssuer: 'https://idp.example.org/realms/NDP',
      oidcClientId: 'ndp-ep-ui',
    });
    expect(isOidcEnabled()).toBe(true);
  });
});

describe('redirect URI', () => {
  it('is built from the origin and the deployment root path', () => {
    expect(getRedirectUri()).toBe(
      `${window.location.origin}/ep-api/ui/auth/callback`
    );
  });
});

describe('callback detection', () => {
  afterEach(() => {
    setUrl('/');
  });

  it('recognises a successful redirect back from the provider', () => {
    setUrl('/ep-api/ui/auth/callback?code=abc&state=xyz');
    expect(isOidcCallback()).toBe(true);
  });

  it('recognises an error redirect back from the provider', () => {
    setUrl('/ep-api/ui/auth/callback?error=access_denied');
    expect(isOidcCallback()).toBe(true);
  });

  it('ignores the callback path without any parameters', () => {
    setUrl('/ep-api/ui/auth/callback');
    expect(isOidcCallback()).toBe(false);
  });

  it('ignores other pages that happen to carry a code parameter', () => {
    setUrl('/ep-api/ui/search?code=abc');
    expect(isOidcCallback()).toBe(false);
  });
});

describe('starting the sign-in', () => {
  afterEach(() => {
    delete window.__EP_CONFIG__;
  });

  it('refuses when no identity provider is configured', async () => {
    delete window.__EP_CONFIG__;
    await expect(beginOidcLogin()).rejects.toThrow(
      /No identity provider is configured/
    );
  });

  // Browsers only expose crypto.subtle in secure contexts, so PKCE cannot be
  // performed over plain http. The flow must refuse rather than silently
  // downgrade to the weaker `plain` challenge method.
  it('refuses over an insecure connection instead of downgrading PKCE', async () => {
    setConfig({
      oidcIssuer: 'https://idp.example.org/realms/NDP',
      oidcClientId: 'ndp-ep-ui',
    });

    const originalSecure = window.isSecureContext;
    Object.defineProperty(window, 'isSecureContext', {
      value: false,
      configurable: true,
    });

    expect(isOidcSupported()).toBe(false);
    await expect(beginOidcLogin()).rejects.toThrow(/secure \(https\) connection/);

    Object.defineProperty(window, 'isSecureContext', {
      value: originalSecure,
      configurable: true,
    });
  });
});
