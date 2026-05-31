import React, { useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { parseGeometry, boundsFromGeometry } from './spatialGeometry';

// Renders the GeoJSON geometry stored in a dataset's `spatial` extra on an
// OpenStreetMap basemap. Returns null when the value cannot be parsed into a
// geometry, so the caller can fall back to plain text.

const STYLE = { color: '#2563eb', weight: 2, fillColor: '#2563eb', fillOpacity: 0.15 };

// Draw point geometries as small circle markers; Leaflet's default marker
// icon relies on image assets that break under the CRA build, and a circle
// reads fine for an extent preview anyway.
const pointToLayer = (_feature, latlng) =>
  L.circleMarker(latlng, { radius: 6, ...STYLE, fillOpacity: 0.6 });

const SpatialMap = ({ spatial, height = 220 }) => {
  const geometry = useMemo(() => parseGeometry(spatial), [spatial]);
  const bounds = useMemo(
    () => (geometry ? boundsFromGeometry(geometry) : null),
    [geometry]
  );

  if (!geometry || !bounds) return null;

  // Leaflet bounds are [[south, west], [north, east]]. Pad a degenerate
  // (single-point) box slightly so the map has something to fit.
  const pad = bounds.minLat === bounds.maxLat ? 0.5 : 0;
  const latLngBounds = [
    [bounds.minLat - pad, bounds.minLng - pad],
    [bounds.maxLat + pad, bounds.maxLng + pad]
  ];

  return (
    <MapContainer
      bounds={latLngBounds}
      boundsOptions={{ padding: [16, 16] }}
      scrollWheelZoom={false}
      style={{
        height: `${height}px`,
        width: '100%',
        borderRadius: '8px',
        border: '1px solid #e2e8f0'
      }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <GeoJSON data={geometry} style={STYLE} pointToLayer={pointToLayer} />
    </MapContainer>
  );
};

export default SpatialMap;
