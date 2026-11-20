import {
  isOidcEnabled,
  isOidcCallback,
  beginOidcLogin,
  completeOidcLogin,
  getOidcLabels,
  markSignedOut,
} from './oidc';
import { authAPI } from './api';

// ./api reads window.__EP_CONFIG__ and constructs an axios client at import
// time; only BASE_URL and the shared validation entry point matter here.
jest.mock('./api', () => ({
  BASE_URL: '/ep-api',
  authAPI: { setAndValidateToken: jest.fn() },
}));

// What entrypoint.sh writes with sign-in on: the Endpoint's own client.
const CONFIG = {
  oidcEnabled: 'True',
  oidcIssuer: 'https://idp.example.org/realms/NDP',
  oidcClientId: 'ep-0123',
  oidcRedirectUri: 'https://ep.example.org/ep-api/ui/auth/callback',
};

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

  // The central guarantee of this feature: a deployment that does not ask for
  // identity-provider sign-in must behave exactly as it did before.
  it('is disabled when no configuration is present', () => {
    delete window.__EP_CONFIG__;
    expect(isOidcEnabled()).toBe(false);
  });

  it('is disabled by default even when everything else is set', () => {
    const { oidcEnabled, ...rest } = CONFIG;
    setConfig(rest);
    expect(isOidcEnabled()).toBe(false);
  });

  it('is disabled when explicitly switched off', () => {
    setConfig({ ...CONFIG, oidcEnabled: 'False' });
    expect(isOidcEnabled()).toBe(false);
  });

  // Half-configured deployments must show nothing rather than a button that
  // fails the moment it is clicked. Without the redirect URI the API would
  // refuse the code.
  it.each(['oidcIssuer', 'oidcClientId', 'oidcRedirectUri'])(
    'stays disabled when switched on but %s is missing',
    (key) => {
      setConfig({ ...CONFIG, [key]: '' });
      expect(isOidcEnabled()).toBe(false);
    }
  );

  it('stays disabled when the values are only whitespace', () => {
    setConfig({
      oidcEnabled: 'True',
      oidcIssuer: '   ',
      oidcClientId: '  ',
      oidcRedirectUri: ' ',
    });
    expect(isOidcEnabled()).toBe(false);
  });

  it('is enabled when switched on and fully configured', () => {
    setConfig(CONFIG);
    expect(isOidcEnabled()).toBe(true);
  });

  // `.env` elsewhere in this project uses Python-style True/False, so the
  // usual spellings must all be understood.
  it.each(['True', 'true', 'TRUE', '1', 'yes', 'on'])(
    'accepts %s as switched on',
    (value) => {
      setConfig({ ...CONFIG, oidcEnabled: value });
      expect(isOidcEnabled()).toBe(true);
    }
  );
});

describe('deployment-supplied wording', () => {
  afterEach(() => {
    delete window.__EP_CONFIG__;
  });

  // Nothing about a particular identity provider may be baked into the build.
  it('falls back to provider-neutral wording', () => {
    delete window.__EP_CONFIG__;
    const { buttonLabel, helpText } = getOidcLabels();
    expect(buttonLabel).toBe('Sign in with your identity provider');
    expect(helpText).toBe('');
  });

  it('uses the label and help text the deployment supplies', () => {
    setConfig({
      oidcButtonLabel: 'Sign in with National Data Platform',
      oidcHelpText: 'Use your institutional credentials, EarthScope or ORCID.',
    });
    const { buttonLabel, helpText } = getOidcLabels();
    expect(buttonLabel).toBe('Sign in with National Data Platform');
    expect(helpText).toBe('Use your institutional credentials, EarthScope or ORCID.');
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
});

// The client's secret stays on the server: the API redeems the code.
describe('signing in with the Endpoint\'s own client', () => {
  const verifier = 'v'.repeat(43);

  const returnFromProvider = () => {
    sessionStorage.setItem('oidcState', 'the-state');
    sessionStorage.setItem('oidcCodeVerifier', verifier);
    setUrl('/ep-api/ui/auth/callback?code=the-code&state=the-state');
  };

  afterEach(() => {
    delete window.__EP_CONFIG__;
    delete global.fetch;
    authAPI.setAndValidateToken.mockReset();
    setUrl('/');
  });

  it('has the API redeem the code, never the identity provider directly', async () => {
    setConfig(CONFIG);
    returnFromProvider();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ access_token: 'the-token' }),
    });
    authAPI.setAndValidateToken.mockResolvedValue({ username: 'jane' });

    await expect(completeOidcLogin()).resolves.toEqual({ username: 'jane' });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toBe('/ep-api/user/oidc/token');
    expect(JSON.parse(init.body)).toEqual({
      code: 'the-code',
      code_verifier: verifier,
    });
    expect(authAPI.setAndValidateToken).toHaveBeenCalledWith('the-token');
  });

  it('refuses a return whose state does not match', async () => {
    setConfig(CONFIG);
    returnFromProvider();
    sessionStorage.setItem('oidcState', 'another-state');
    global.fetch = jest.fn();

    await expect(completeOidcLogin()).rejects.toThrow(/could not be verified/);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("shows the API's reason when the code is refused", async () => {
    setConfig(CONFIG);
    returnFromProvider();
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: () =>
        Promise.resolve({ detail: 'The identity provider did not accept the sign-in' }),
    });

    await expect(completeOidcLogin()).rejects.toThrow(
      /did not accept the sign-in/
    );
    expect(authAPI.setAndValidateToken).not.toHaveBeenCalled();
  });

  // Browsers only expose crypto.subtle in secure contexts, so over plain http
  // the sign-in goes without PKCE.
  describe('over plain http', () => {
    let originalSecure;
    let originalCrypto;
    beforeEach(() => {
      originalSecure = window.isSecureContext;
      originalCrypto = window.crypto;
      Object.defineProperty(window, 'isSecureContext', {
        value: false,
        configurable: true,
      });
      // What a browser offers over http: random values, but no crypto.subtle.
      Object.defineProperty(window, 'crypto', {
        value: {
          getRandomValues: (bytes) => require('crypto').randomFillSync(bytes),
        },
        configurable: true,
      });
    });
    afterEach(() => {
      Object.defineProperty(window, 'isSecureContext', {
        value: originalSecure,
        configurable: true,
      });
      Object.defineProperty(window, 'crypto', {
        value: originalCrypto,
        configurable: true,
      });
      sessionStorage.clear();
    });

    it('starts without a PKCE challenge, with a state', async () => {
      setConfig(CONFIG);
      const assign = jest.fn();
      const originalLocation = window.location;
      delete window.location;
      window.location = { ...originalLocation, assign };

      try {
        await beginOidcLogin();
      } finally {
        window.location = originalLocation;
      }

      const url = new URL(assign.mock.calls[0][0]);
      expect(`${url.origin}${url.pathname}`).toBe(
        'https://idp.example.org/realms/NDP/protocol/openid-connect/auth'
      );
      expect(url.searchParams.get('client_id')).toBe('ep-0123');
      expect(url.searchParams.get('redirect_uri')).toBe(
        'https://ep.example.org/ep-api/ui/auth/callback'
      );
      expect(url.searchParams.get('state')).toBe(
        sessionStorage.getItem('oidcState')
      );
      expect(url.searchParams.has('code_challenge')).toBe(false);
      expect(sessionStorage.getItem('oidcCodeVerifier')).toBeNull();
    });

    // As in the AAI console: after signing out of the Endpoint, the next
    // sign-in asks for credentials instead of reusing the provider session.
    it('asks for credentials again after a sign-out', async () => {
      setConfig(CONFIG);
      const assign = jest.fn();
      const originalLocation = window.location;
      delete window.location;
      window.location = { ...originalLocation, assign };

      try {
        await beginOidcLogin();
        markSignedOut();
        await beginOidcLogin();
      } finally {
        window.location = originalLocation;
        localStorage.clear();
      }

      const first = new URL(assign.mock.calls[0][0]);
      const second = new URL(assign.mock.calls[1][0]);
      expect(first.searchParams.has('prompt')).toBe(false);
      expect(second.searchParams.get('prompt')).toBe('login');
    });

    it('finishes without a verifier', async () => {
      setConfig(CONFIG);
      sessionStorage.setItem('oidcState', 'the-state');
      setUrl('/ep-api/ui/auth/callback?code=the-code&state=the-state');
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ access_token: 'the-token' }),
      });
      authAPI.setAndValidateToken.mockResolvedValue({ username: 'jane' });

      markSignedOut();

      await expect(completeOidcLogin()).resolves.toEqual({ username: 'jane' });

      expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({
        code: 'the-code',
      });
      // Signed in again: the next sign-in may reuse the provider session.
      expect(localStorage.getItem('oidcReauth')).toBeNull();
    });
  });
});
