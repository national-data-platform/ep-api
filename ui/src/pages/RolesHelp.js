import React from 'react';
import { ShieldAlert, ArrowLeft, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

/**
 * In-app runbook for adding a new role. Deliberately terse and
 * procedural — no conceptual intro. Reached from the "Add more roles"
 * button on the Access Requests page.
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
  const aai = 'https://idp.nationaldataplatform.org'; // AAI base (AUTH_API_URL host)
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
          A role is a Keycloak realm role named{' '}
          <C>group:&#123;EP_UUID&#125;:&#123;name&#125;</C>, where{' '}
          <C>EP_UUID</C> is this deployment&apos;s <C>AFFINITIES_EP_UUID</C>.
          Replace <C>$EP_UUID</C>, <C>$ADMIN_TOKEN</C> (a group-admin&apos;s
          bearer token) and <C>$USER</C> below.
        </p>

        <StepTitle n={1}>Create the role (AAI API)</StepTitle>
        <p style={{ color: '#475569', lineHeight: 1.55, margin: 0 }}>
          <C>roleName</C> is the <strong>bare</strong> name — the AAI prefixes{' '}
          <C>group:$EP_UUID:</C> itself. The names <C>admin</C>, <C>editor</C>{' '}
          and <C>viewer</C> are reserved and rejected.
        </p>
        <Pre>{`curl -X POST "${aai}/role/create" \\
  -H "Authorization: Bearer $ADMIN_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"groupName":"'$EP_UUID'","roleName":"publisher"}'
# -> 201 {"role":"group:$EP_UUID:publisher"}`}</Pre>
        <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
          (Step 2 auto-creates the role too if you skip this, but creating it
          explicitly lets you assign to many users at once with{' '}
          <C>&quot;users&quot;:[…]</C>.)
        </p>

        <StepTitle n={2}>Assign it to a user (AAI API)</StepTitle>
        <p style={{ color: '#475569', lineHeight: 1.55, margin: 0 }}>
          Again the <strong>bare</strong> name plus <C>groupName</C>. Do not
          pass the full <C>group:…:publisher</C> string — it double-prefixes
          and fails.
        </p>
        <Pre>{`curl -X POST "${aai}/role/assign" \\
  -H "Authorization: Bearer $ADMIN_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"groupName":"'$EP_UUID'","roleName":"publisher","username":"'$USER'"}'`}</Pre>
        <p style={{ color: '#475569', lineHeight: 1.55, margin: 0 }}>
          The user must <strong>log out and back in</strong> — the new role
          only appears in a freshly minted JWT. No Keycloak client change is
          needed; the realm-roles mapper puts it in the token automatically.
          Verify with <C>GET /user/info</C> (look at the <C>roles</C> array).
        </p>

        <StepTitle n={3}>Make the Endpoint enforce it (code change)</StepTitle>
        <p style={{ color: '#475569', lineHeight: 1.55, margin: 0 }}>
          Steps 1–2 put the role in the token, but the Endpoint only grants
          permissions for <C>admin</C> / <C>writer</C> / <C>viewer</C>. Any
          other role rides in the token and grants nothing. To make{' '}
          <C>publisher</C> actually do something, edit{' '}
          <C>api/services/auth_services/authorization_service.py</C>:
        </p>
        <ul style={{ color: '#475569', lineHeight: 1.7, paddingLeft: '1.4rem' }}>
          <li>
            Add a matcher, e.g. <C>is_publisher()</C>, reusing{' '}
            <C>_has_any_role(user_info, [endpoint_group_role_name(&quot;publisher&quot;), &quot;ndp_publisher&quot;])</C>.
          </li>
          <li>
            Fold it into <C>effective_role()</C> at the right precedence.
          </li>
          <li>
            Create/extend a dependency (like{' '}
            <C>get_user_for_write_operation</C>) and apply it to the routes the
            role should guard.
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
          If you only need <strong>viewer / writer / admin</strong> (in this or
          another group), skip steps 1 and 3 entirely — just assign the
          existing tier via the Access Requests screen. Step 3 is only for a
          genuinely new permission level, and is the part to{' '}
          <strong>request from NDP support</strong> if you can&apos;t change
          the Endpoint code.
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
            Full reference (naming, JWT flow, AAI surface)
            <ExternalLink size={16} />
          </a>
        </p>
      </div>
    </div>
  );
};

export default RolesHelp;
