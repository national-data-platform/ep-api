import {
  isOidcEnabled,
  isOidcSupported,
  isOidcCallback,
  getRedirectUri,
  beginOidcLogin,
  getOidcLabels,
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

  // The central guarantee of this feature: a deployment that does not ask for
  // identity-provider sign-in must behave exactly as it did before.
  it('is disabled when no configuration is present', () => {
    delete window.__EP_CONFIG__;
    expect(isOidcEnabled()).toBe(false);
  });

  it('is disabled by default even when issuer and client id are set', () => {
    setConfig({
      oidcIssuer: 'https://idp.example.org/realms/NDP',
      oidcClientId: 'ndp-ep-ui',
    });
    expect(isOidcEnabled()).toBe(false);
  });

  it('is disabled when explicitly switched off', () => {
    setConfig({
      oidcEnabled: 'False',
      oidcIssuer: 'https://idp.example.org/realms/NDP',
      oidcClientId: 'ndp-ep-ui',
    });
    expect(isOidcEnabled()).toBe(false);
  });

  // Half-configured deployments must show nothing rather than a button that
  // fails the moment it is clicked.
  it('stays disabled when switched on but the issuer is missing', () => {
    setConfig({ oidcEnabled: 'True', oidcClientId: 'ndp-ep-ui' });
    expect(isOidcEnabled()).toBe(false);
  });

  it('stays disabled when switched on but the client id is missing', () => {
    setConfig({
      oidcEnabled: 'True',
      oidcIssuer: 'https://idp.example.org/realms/NDP',
    });
    expect(isOidcEnabled()).toBe(false);
  });

  it('stays disabled when the values are only whitespace', () => {
    setConfig({ oidcEnabled: 'True', oidcIssuer: '   ', oidcClientId: '  ' });
    expect(isOidcEnabled()).toBe(false);
  });

  it('is enabled when switched on and fully configured', () => {
    setConfig({
      oidcEnabled: 'True',
      oidcIssuer: 'https://idp.example.org/realms/NDP',
      oidcClientId: 'ndp-ep-ui',
    });
    expect(isOidcEnabled()).toBe(true);
  });

  // `.env` elsewhere in this project uses Python-style True/False, so the
  // usual spellings must all be understood.
  it.each(['True', 'true', 'TRUE', '1', 'yes', 'on'])(
    'accepts %s as switched on',
    (value) => {
      setConfig({
        oidcEnabled: value,
        oidcIssuer: 'https://idp.example.org/realms/NDP',
        oidcClientId: 'ndp-ep-ui',
      });
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
      oidcEnabled: 'True',
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
