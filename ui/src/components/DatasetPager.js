import React from 'react';

// "Showing N of M" under the dataset results, and a button for the next page
// while the catalog has more matches (issue #420). Nothing when the search
// reported no total. With "Only mine", M counts everyone's datasets, so the
// line says how many matches were looked through instead.
export default function DatasetPager({
  shown,
  total,
  hasMore,
  loading,
  error,
  onLoadMore,
  onlyMine = false,
  lookedAt = null
}) {
  if (total === null || total === undefined) return null;
  const line = onlyMine
    ? `Showing ${shown} of yours among the first ${lookedAt ?? total} of ${total} matching datasets`
    : `Showing ${shown} of ${total} matching datasets`;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
        flexWrap: 'wrap',
        margin: '-0.5rem 0 1.5rem'
      }}
    >
      <span style={{ color: '#6b7280', fontSize: '0.9rem' }}>{line}</span>
      {hasMore && (
        <button
          type="button"
          className="btn btn-outline-primary btn-sm"
          onClick={onLoadMore}
          disabled={loading}
        >
          {loading ? 'Loading…' : 'Load more'}
        </button>
      )}
      {error && (
        <span role="alert" style={{ color: '#b91c1c', fontSize: '0.9rem', width: '100%' }}>
          {error}
        </span>
      )}
    </div>
  );
}
