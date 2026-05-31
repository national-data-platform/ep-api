import React from 'react';
import { MapPin } from 'lucide-react';
import SpatialMap from './SpatialMap';
import { parseGeometry } from './spatialGeometry';

// Renders a dataset's CKAN `extras` in a readable way: the spatial extent is
// drawn on a map, the remaining fields get human-friendly labels, and harvest
// provenance is split into its own muted subsection. All values present in
// `extras` are still surfaced — nothing is hidden.

// Friendly labels for keys we know about. Anything not listed falls back to a
// humanized version of the raw key.
const LABELS = {
  EPSG: 'EPSG',
  collection: 'Collection',
  data_vintage: 'Data vintage',
  encoding: 'Encoding',
  resolution: 'Resolution',
  service_type: 'Service type',
  harvest_object_id: 'Harvest object ID',
  harvest_source_id: 'Harvest source ID',
  harvest_source_title: 'Harvest source',
  ndp_user_id: 'Owner ID',
  status: 'Status'
};

const humanize = (key) =>
  key
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();

const labelFor = (key) => LABELS[key] || humanize(key);

const formatValue = (value) =>
  typeof value === 'object' && value !== null
    ? JSON.stringify(value)
    : String(value);

// Long opaque values (UUIDs, hashes) read better in a monospace font that can
// wrap, so the rest of the grid stays aligned.
const isOpaque = (value) =>
  typeof value === 'string' && /^[0-9a-f-]{16,}$/i.test(value);

const Field = ({ label, value }) => (
  <div style={{ fontSize: '0.85rem' }}>
    <div style={{ color: '#64748b', fontWeight: 500, marginBottom: '0.1rem' }}>{label}</div>
    <div
      style={{
        color: '#0f172a',
        wordBreak: 'break-word',
        fontFamily: isOpaque(value) ? 'monospace' : 'inherit',
        fontSize: isOpaque(value) ? '0.78rem' : '0.85rem'
      }}
    >
      {formatValue(value)}
    </div>
  </div>
);

const FieldGrid = ({ entries }) => (
  <div
    style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: '0.65rem'
    }}
  >
    {entries.map(([key, value]) => (
      <Field key={key} label={labelFor(key)} value={value} />
    ))}
  </div>
);

const DatasetMetadata = ({ extras }) => {
  const entries = Object.entries(extras || {});
  if (!entries.length) return null;

  const spatialEntry = entries.find(([key]) => key === 'spatial');
  const spatial = spatialEntry ? spatialEntry[1] : null;
  const canMapSpatial = spatial != null && parseGeometry(spatial) != null;

  // Fields shown in the main grid: everything except spatial (handled by the
  // map) and harvest provenance (its own subsection). If the spatial value
  // cannot be drawn, keep it here as plain text so no information is lost.
  const general = entries.filter(([key]) => {
    if (key.startsWith('harvest_')) return false;
    if (key === 'spatial') return !canMapSpatial;
    return true;
  });
  const harvest = entries.filter(([key]) => key.startsWith('harvest_'));

  return (
    <div
      style={{
        marginTop: '0.75rem',
        padding: '0.9rem',
        background: '#f8fafc',
        borderRadius: '8px',
        border: '1px solid #e2e8f0',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.9rem'
      }}
    >
      {canMapSpatial && (
        <div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              color: '#64748b',
              fontWeight: 500,
              fontSize: '0.85rem',
              marginBottom: '0.4rem'
            }}
          >
            <MapPin size={14} />
            Spatial extent
          </div>
          <SpatialMap spatial={spatial} />
        </div>
      )}

      {general.length > 0 && <FieldGrid entries={general} />}

      {harvest.length > 0 && (
        <div
          style={{
            borderTop: '1px solid #e2e8f0',
            paddingTop: '0.75rem'
          }}
        >
          <div
            style={{
              color: '#94a3b8',
              fontWeight: 600,
              fontSize: '0.72rem',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
              marginBottom: '0.5rem'
            }}
          >
            Harvest provenance
          </div>
          <FieldGrid entries={harvest} />
        </div>
      )}
    </div>
  );
};

export default DatasetMetadata;
