import { isAccessRequestAdmin } from './api';

describe('isAccessRequestAdmin', () => {
  it('uses effective_role when the backend provides it', () => {
    expect(isAccessRequestAdmin({ roles: [], effective_role: 'admin' })).toBe(true);
  });

  it('accepts Keycloak group-path admin roles as a fallback', () => {
    expect(
      isAccessRequestAdmin({
        roles: ['group:ndp_ep/ep-6a619d3f8b9242b94b015efb:admin'],
      })
    ).toBe(true);
  });

  it('rejects endpoint group membership without an admin role', () => {
    expect(
      isAccessRequestAdmin({
        roles: ['default-roles-ndp'],
        groups: ['ndp_ep/ep-6a619d3f8b9242b94b015efb'],
        effective_role: 'none',
      })
    ).toBe(false);
  });
});
