import {
  appendNew,
  DATASET_PAGE,
  nextOffsetAfter,
  requestDatasetPage,
  totalOf
} from './searchPaging';

describe('totalOf', () => {
  test('reads the number of matches from X-Total-Count', () => {
    expect(totalOf({ headers: { 'x-total-count': '1124' } })).toBe(1124);
  });

  test.each([[undefined], [{}], [{ headers: {} }], [{ headers: { 'x-total-count': 'x' } }]])(
    'is null without a usable header (%p)',
    (response) => {
      expect(totalOf(response)).toBeNull();
    }
  );
});

describe('nextOffsetAfter', () => {
  test('points past the page while more match', () => {
    expect(nextOffsetAfter(0, DATASET_PAGE, 1124)).toBe(100);
    expect(nextOffsetAfter(1000, DATASET_PAGE, 1124)).toBe(1100);
  });

  test('is null once every match was asked for, or without a total', () => {
    expect(nextOffsetAfter(1100, DATASET_PAGE, 1124)).toBeNull();
    expect(nextOffsetAfter(0, DATASET_PAGE, 100)).toBeNull();
    expect(nextOffsetAfter(0, DATASET_PAGE, null)).toBeNull();
  });
});

describe('appendNew', () => {
  test('adds a page without repeating what is shown', () => {
    const shown = [{ id: 'a' }, { id: 'b' }];
    expect(appendNew(shown, [{ id: 'b' }, { id: 'c' }]).map((d) => d.id)).toEqual(['a', 'b', 'c']);
  });
});

// The organization filter pages too (issue #424): POST /search takes the
// same offset and limit as GET /search.
describe('requestDatasetPage', () => {
  const fakeSearchAPI = () => {
    const calls = [];
    return {
      calls,
      searchByTerms: (...args) => {
        calls.push(['terms', ...args]);
        return Promise.resolve('terms');
      },
      searchAdvanced: (...args) => {
        calls.push(['advanced', ...args]);
        return Promise.resolve('advanced');
      }
    };
  };

  test('a term search asks GET /search for the page', async () => {
    const api = fakeSearchAPI();
    await requestDatasetPage(api, { term: 'gnss', server: 'global', ownerOrg: '' }, 200);
    expect(api.calls).toEqual([
      ['terms', ['gnss'], null, 'global', { offset: 200, limit: DATASET_PAGE }]
    ]);
  });

  test('an organization search asks POST /search for the page', async () => {
    const api = fakeSearchAPI();
    await requestDatasetPage(api, { term: 'water', server: 'local', ownerOrg: 'big-org' }, 100);
    expect(api.calls).toEqual([
      [
        'advanced',
        { owner_org: 'big-org', search_term: 'water', server: 'local' },
        { offset: 100, limit: DATASET_PAGE }
      ]
    ]);
  });

  test('an organization search without a term sends no search_term', async () => {
    const api = fakeSearchAPI();
    await requestDatasetPage(api, { term: '', server: 'local', ownerOrg: 'big-org' }, 0);
    expect(api.calls[0][1]).toEqual({ owner_org: 'big-org', search_term: undefined, server: 'local' });
  });
});
