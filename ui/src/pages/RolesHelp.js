import React from 'react';
import { ShieldAlert, ArrowLeft, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

/**
 * In-app runbook for checking a permission and adding a permission level.
 * Deliberately terse and procedural — no conceptual intro. Reached from the
 * "Add more roles" button on the Access Requests page.
 */
const Pre = ({ children }) => (
  <pre
    style={{
      background: '#0f172a',
      color: '#e2e8f0',
      borderRadius: '8px',
      padding: '0.9rem 1rem',
      overflowX: 'auto',
      fontSize: '0.82rem',
      lineHeight: 1.5,
      margin: '0.5rem 0 1rem'
    }}
  >
    <code>{children}</code>
  </pre>
);

const C = ({ children }) => (
  <code
    style={{
      background: '#f1f5f9',
      borderRadius: '4px',
      padding: '0.1rem 0.35rem',
      fontSize: '0.85em',
      fontFamily: 'monospace',
      color: '#0f172a',
      wordBreak: 'break-word'
    }}
  >
    {children}
  </code>
);

const StepTitle = ({ n, children }) => (
  <h2
    style={{
      fontSize: '1.05rem',
      fontWeight: 700,
      color: '#1e293b',
      marginTop: '1.75rem',
      marginBottom: '0.5rem'
    }}
  >
    {n}. {children}
  </h2>
);

const RolesHelp = () => {
  const navigate = useNavigate();
  const idp = 'https://idp.nationaldataplatform.org'; // KEYCLOAK_URL
  const docUrl =
    'https://github.com/national-data-platform/ep-api/blob/main/docs/roles-and-permissions.md';

  return (
    <div style={{ maxWidth: '820px', margin: '0 auto', padding: '0 1rem' }}>
      <div className="page-header">
        <h1 className="page-title">
          <ShieldAlert size={32} style={{ marginRight: '0.5rem' }} />
          Add a new role
        </h1>
      </div>

      <button
        type="button"
        onClick={() => navigate('/access-requests')}
        className="btn btn-secondary"
        style={{ marginBottom: '1rem' }}
      >
        <ArrowLeft size={16} />
        Back to Access Requests
      </button>

      <div className="card">
        <p style={{ margin: 0, color: '#475569', lineHeight: 1.55 }}>
          Keycloak decides what a user may do here, through the permission
          gates of this Endpoint&apos;s client (<C>OIDC_SERVICE_CLIENT_ID</C>,{' '}
          <C>ep-&#123;config-id&#125;</C>). The tiers are levels of the
          Endpoint&apos;s group: <C>viewers</C> pass <C>viewer-area</C>,{' '}
          <C>editors</C> (the writer tier) <C>editor-area</C>, <C>admins</C>{' '}
          <C>admin-area</C>. The <C>roles</C> in <C>GET /user/info</C> decide
          nothing. Replace <C>$CLIENT</C>, <C>$USER_TOKEN</C> (the
          user&apos;s bearer token) and <C>$GATE</C> below.
        </p>

        <StepTitle n={1}>Check what Keycloak decides</StepTitle>
        <p style={{ color: '#475569', lineHeight: 1.55, margin: 0 }}>
          The same request the Endpoint sends for every guarded route:
        </p>
        <Pre>{`curl -s -X POST "${idp}/realms/NDP/protocol/openid-connect/token" \\
  -H "Authorization: Bearer $USER_TOKEN" \\
  -d grant_type=urn:ietf:params:oauth:grant-type:uma-ticket \\
  -d audience=$CLIENT -d permission=$GATE -d response_mode=decision
# -> {"result":true}, or 403 "not_authorized"`}</Pre>
        <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
          A <C>400</C> means the client does not exist or has no such gate —
          ask NDP support to link it to the Endpoint&apos;s group.
        </p>

        <StepTitle n={2}>Create the level (NDP support)</StepTitle>
        <p style={{ color: '#475569', lineHeight: 1.55, margin: 0 }}>
          A new level, say <C>publisher</C>, is a permission level of the
          Endpoint&apos;s group that the AAI turns into a{' '}
          <C>publisher-area</C> gate on the client, passed by its members and
          the group&apos;s admins. It is created with{' '}
          <C>customPermissions</C> when the client is created; for an
          existing Endpoint, ask NDP support.
        </p>

        <StepTitle n={3}>Make the Endpoint enforce it (code change)</StepTitle>
        <p style={{ color: '#475569', lineHeight: 1.55, margin: 0 }}>
          The Endpoint only asks for <C>admin-area</C>, <C>editor-area</C> and{' '}
          <C>viewer-area</C>. To make <C>publisher</C> actually do something,
          edit <C>api/services/auth_services/</C>:
        </p>
        <ul style={{ color: '#475569', lineHeight: 1.7, paddingLeft: '1.4rem' }}>
          <li>
            In <C>ep_access_gate.py</C>, add <C>ep_publisher_gate</C>, built
            like <C>ep_editor_gate</C> but asking{' '}
            <C>ep_access_gate(token, &quot;publisher-area&quot;)</C>, and apply
            it to the routes the level should guard.
          </li>
          <li>
            If the UI should know, fold it into <C>_effective_role()</C> in{' '}
            <C>user_info.py</C> at the right precedence.
          </li>
          <li>Add tests, bump the version, redeploy.</li>
        </ul>
        <p
          style={{
            background: '#fffbeb',
            border: '1px solid #fde68a',
            borderRadius: '8px',
            padding: '0.75rem 1rem',
            color: '#78350f',
            fontSize: '0.9rem',
            lineHeight: 1.5,
            marginTop: '0.5rem'
          }}
        >
          If you only need <strong>viewer / writer / admin</strong>, skip
          steps 2 and 3 entirely — approve the tier on the Access Requests
          screen, which adds the user to the group at that level. It applies
          from their next request. Steps 2 and 3 are only for a genuinely new
          permission level; <strong>request them from NDP support</strong> if
          you can&apos;t change the Endpoint code.
        </p>

        <p style={{ marginTop: '1.25rem', marginBottom: 0 }}>
          <a
            href={docUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: '#2563eb',
              fontWeight: 600,
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem'
            }}
          >
            Full reference (gates, decision call, AAI surface)
            <ExternalLink size={16} />
          </a>
        </p>
      </div>
    </div>
  );
};

export default RolesHelp;
