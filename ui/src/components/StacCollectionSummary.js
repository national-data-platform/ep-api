import React, { useEffect, useMemo, useState } from 'react';
import { Download, ChevronDown, ChevronRight } from 'lucide-react';
import { stacAPI } from '../services/api';
import SpatialMap from './SpatialMap';

// A summary of the STAC collection a dataset's resource points to (#405):
// extent, counts, summaries, and the items, which can be filtered by name and
// opened one at a time to get their download links. The Endpoint reads the
// collection, so this works without CORS on the file server.

const PAGE = 20;

// A resource worth offering a summary for. The server checks that it really is
// a STAC collection; this only decides whether to show the button.
export const looksLikeStacCollection = (resource) => {
  if (!resource || !resource.url || !resource.id) return false;
  const format = (resource.format || '').toLowerCase();
  let path = '';
  try {
    path = new URL(resource.url).pathname.toLowerCase();
  } catch {
    return false;
  }
  return format.includes('stac') || path.endsWith('/collection.json');
};

export const bboxToGeometry = (bbox) => {
  if (!Array.isArray(bbox) || (bbox.length !== 4 && bbox.length !== 6)) return null;
  const [west, south, east, north] =
    bbox.length === 4 ? bbox : [bbox[0], bbox[1], bbox[3], bbox[4]];
  return {
    type: 'Polygon',
    coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]]
  };
};

const year = (value) => (typeof value === 'string' ? value.slice(0, 4) : null);

export const periodLabel = (interval) => {
  if (!Array.isArray(interval)) return null;
  const [start, end] = interval.map(year);
  if (!start && !end) return null;
  return `${start || '…'}–${end || '…'}`;
};

const errorText = (err) =>
  err?.response?.data?.detail || err?.message || 'The collection could not be read.';

const Stat = ({ label, value }) => (
  <div style={{ background: '#f1f5f9', borderRadius: '6px', padding: '0.5rem 0.75rem', minWidth: '7rem' }}>
    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{label}</div>
    <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#0f172a' }}>{value}</div>
  </div>
);

const SummaryLine = ({ summary }) => {
  const [all, setAll] = useState(false);
  if (summary.values) {
    const shown = all ? summary.values : summary.values.slice(0, 8);
    const hidden = summary.count - shown.length;
    return (
      <div style={{ fontSize: '0.85rem', color: '#475569' }}>
        <strong style={{ color: '#0f172a' }}>{summary.name}</strong>: {shown.join(', ')}
        {hidden > 0 && (
          <button type="button" onClick={() => setAll(true)} style={linkButton}>
            +{hidden} more
          </button>
        )}
      </div>
    );
  }
  return (
    <div style={{ fontSize: '0.85rem', color: '#475569' }}>
      <strong style={{ color: '#0f172a' }}>{summary.name}</strong>: {String(summary.minimum)} – {String(summary.maximum)}
    </div>
  );
};

const linkButton = {
  background: 'none',
  border: 'none',
  color: '#2563eb',
  cursor: 'pointer',
  padding: '0 0 0 0.35rem',
  fontSize: '0.85rem'
};

const ItemRow = ({ item, server, datasetId, resourceId }) => {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState({ loading: false, error: null, data: null });

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next && !state.data && !state.loading) {
      setState({ loading: true, error: null, data: null });
      stacAPI
        .item(server, datasetId, resourceId, item.href)
        .then((res) => setState({ loading: false, error: null, data: res.data }))
        .catch((err) => setState({ loading: false, error: errorText(err), data: null }));
    }
  };

  const props = state.data?.properties || {};
  const period = periodLabel([props.start_datetime || props.datetime, props.end_datetime]);

  return (
    <div style={{ borderTop: '1px solid #e2e8f0', padding: '0.4rem 0' }}>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        style={{ ...linkButton, padding: 0, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '0.35rem', fontFamily: 'monospace', fontSize: '0.8rem', textAlign: 'left' }}
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {item.id}
      </button>
      {open && (
        <div style={{ padding: '0.35rem 0 0.25rem 1.25rem', fontSize: '0.85rem', color: '#475569' }}>
          {state.loading && <div>Loading…</div>}
          {state.error && <div style={{ color: '#b91c1c' }}>{state.error}</div>}
          {state.data && (
            <>
              {period && <div>Period: {period}</div>}
              {state.data.assets.length === 0 && <div>This item has no files.</div>}
              {state.data.assets.map((asset) => (
                <div key={asset.key}>
                  <a href={asset.href} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                    <Download size={14} />
                    {asset.title}
                  </a>
                  {asset.type && <span style={{ color: '#94a3b8' }}> · {asset.type}</span>}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
};

const StacCollectionSummary = ({ server, datasetId, resourceId }) => {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [filter, setFilter] = useState('');
  const [shown, setShown] = useState(PAGE);

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: null, data: null });
    stacAPI
      .collection(server, datasetId, resourceId)
      .then((res) => !cancelled && setState({ loading: false, error: null, data: res.data }))
      .catch((err) => !cancelled && setState({ loading: false, error: errorText(err), data: null }));
    return () => {
      cancelled = true;
    };
  }, [server, datasetId, resourceId]);

  const matches = useMemo(() => {
    const items = state.data?.items || [];
    const terms = filter.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) return items;
    return items.filter((item) => terms.every((t) => item.id.toLowerCase().includes(t)));
  }, [state.data, filter]);

  const box = { marginTop: '0.5rem', border: '1px solid #bfdbfe', borderRadius: '8px', padding: '0.75rem 1rem', background: '#ffffff' };

  if (state.loading) return <div style={box}>Reading the STAC collection…</div>;
  if (state.error) return <div style={{ ...box, color: '#b91c1c' }}>{state.error}</div>;

  const c = state.data;
  const geometry = bboxToGeometry(c.bbox);
  const period = periodLabel(c.interval);

  return (
    <div style={box} data-testid="stac-summary">
      <div style={{ fontWeight: 600, color: '#0f172a' }}>{c.title || c.id}</div>
      {c.description && (
        <div style={{ color: '#475569', fontSize: '0.85rem', margin: '0.25rem 0 0.75rem' }}>{c.description}</div>
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <Stat label="Items" value={c.item_count.toLocaleString()} />
        {period && <Stat label="Period" value={period} />}
        {c.summaries
          .filter((s) => s.values && s.count > 1)
          .slice(0, 3)
          .map((s) => (
            <Stat key={s.name} label={s.name} value={s.count} />
          ))}
        {c.license && <Stat label="License" value={c.license} />}
      </div>
      {geometry && (
        <div style={{ marginBottom: '0.75rem' }}>
          <SpatialMap spatial={geometry} height={180} />
        </div>
      )}
      {c.summaries.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginBottom: '0.75rem' }}>
          {c.summaries.map((s) => (
            <SummaryLine key={s.name} summary={s} />
          ))}
        </div>
      )}
      {c.item_count > 0 && (
        <>
          <input
            type="search"
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value);
              setShown(PAGE);
            }}
            placeholder="Filter items by name, e.g. MIROC6 ssp370"
            aria-label="Filter items by name"
            style={{ width: '100%', padding: '0.4rem 0.6rem', border: '1px solid #cbd5e1', borderRadius: '6px', marginBottom: '0.5rem', boxSizing: 'border-box' }}
          />
          {matches.slice(0, shown).map((item) => (
            <ItemRow key={item.href} item={item} server={server} datasetId={datasetId} resourceId={resourceId} />
          ))}
          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.35rem' }}>
            Showing {Math.min(shown, matches.length)} of {matches.length.toLocaleString()}
            {filter ? ' matching' : ''} items.
            {matches.length > shown && (
              <button type="button" onClick={() => setShown(shown + PAGE)} style={linkButton}>
                Show more
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default StacCollectionSummary;
