/**
 * Role helpers, kept free of any network dependency so they can be unit
 * tested without pulling in the axios client.
 */

/**
 * Return true if the given `/user/info` payload grants admin access to the
 * management areas (admin dashboard, access-request review).
 *
 * The authority on this is the backend, which reports `effective_role` after
 * resolving every admin role form — including the endpoint-scoped
 * `group:{UUID}:admin` — so we trust that value. Re-deriving admin status from
 * role strings here is what caused endpoint admins to be locked out: the old
 * check matched only `ndp_admin` or names ending in `_admin`, missing the
 * canonical `group:{UUID}:admin` (which ends in `:admin`).
 *
 * The role-string fallback is kept only for an older backend that does not
 * send `effective_role`, and it now also recognizes the `:admin` form.
 */
export const isAccessRequestAdmin = (userInfo) => {
  const effective = userInfo?.effective_role;
  if (typeof effective === 'string') {
    return effective.trim().toLowerCase() === 'admin';
  }

  const roles = userInfo?.roles;
  if (!Array.isArray(roles)) return false;
  return roles.some((role) => {
    if (typeof role !== 'string') return false;
    const lower = role.trim().toLowerCase();
    return (
      lower === 'ndp_admin' ||
      lower.endsWith('_admin') ||
      lower.endsWith(':admin')
    );
  });
};
