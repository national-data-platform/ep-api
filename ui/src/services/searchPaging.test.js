import { appendNew, DATASET_PAGE, nextOffsetAfter, totalOf } from './searchPaging';

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
