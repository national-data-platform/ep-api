// Search results a page at a time (issue #420). GET /search takes offset and
// limit and says in X-Total-Count how many datasets the catalog matched, so
// the Search page shows the first page and loads the rest on demand instead
// of stopping silently at 1000.

export const DATASET_PAGE = 100;

// The number of matches a /search response reports, or null.
export const totalOf = (response) => {
  const raw = response?.headers?.['x-total-count'];
  if (raw === undefined || raw === null || raw === '') return null;
  const total = Number(raw);
  return Number.isFinite(total) && total >= 0 ? total : null;
};

// Where the next page starts, or null when there is nothing more. The
// Endpoint can drop a few matches of a page (it checks every term), so the
// position advances by what was asked for, not by what came back.
export const nextOffsetAfter = (offset, limit, total) => {
  const next = offset + limit;
  return total !== null && next < total ? next : null;
};

// Append a page, skipping datasets already shown.
export const appendNew = (shown, page) => {
  const seen = new Set(shown.map((item) => item.id));
  return [...shown, ...page.filter((item) => !seen.has(item.id))];
};
