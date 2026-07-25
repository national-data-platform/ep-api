import { isAccessRequestAdmin } from './roles';

describe('isAccessRequestAdmin', () => {
  // The bug this guards: an endpoint administrator, whose role is the
  // canonical group:{uuid}:admin, was denied the management areas because the
  // UI matched only ndp_admin / *_admin.
  it('trusts the backend effective_role when present', () => {
    expect(isAccessRequestAdmin({ effective_role: 'admin' })).toBe(true);
    expect(isAccessRequestAdmin({ effective_role: 'writer' })).toBe(false);
    expect(isAccessRequestAdmin({ effective_role: 'viewer' })).toBe(false);
    expect(isAccessRequestAdmin({ effective_role: 'none' })).toBe(false);
  });

  it('lets effective_role override the raw roles array', () => {
    // A platform admin role is present, but effective_role says the caller is
    // not an admin on this endpoint — the authoritative value wins.
    expect(
      isAccessRequestAdmin({ effective_role: 'viewer', roles: ['ndp_admin'] })
    ).toBe(false);
  });

  // Fallback path, for a backend old enough not to send effective_role.
  describe('role-string fallback (no effective_role)', () => {
    it('recognizes the platform admin role', () => {
      expect(isAccessRequestAdmin({ roles: ['ndp_admin'] })).toBe(true);
    });

    it('recognizes the canonical endpoint admin role', () => {
      expect(isAccessRequestAdmin({ roles: ['group:6a4bd301-ab:admin'] })).toBe(
        true
      );
    });

    it('recognizes the legacy endpoint admin role', () => {
      expect(isAccessRequestAdmin({ roles: ['6a4bd301-ab_admin'] })).toBe(true);
    });

    it('denies a non-admin', () => {
      expect(
        isAccessRequestAdmin({ roles: ['group:6a4bd301-ab:writer', 'user'] })
      ).toBe(false);
    });

    it('handles missing or malformed input', () => {
      expect(isAccessRequestAdmin(undefined)).toBe(false);
      expect(isAccessRequestAdmin({})).toBe(false);
      expect(isAccessRequestAdmin({ roles: 'ndp_admin' })).toBe(false);
      expect(isAccessRequestAdmin({ roles: [null, 42] })).toBe(false);
    });
  });
});
