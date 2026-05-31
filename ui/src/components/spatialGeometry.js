// Pure helpers for turning a dataset's `spatial` extra into a GeoJSON geometry
// and a bounding box. Kept free of Leaflet (and any DOM dependency) so the
// logic can be unit-tested and imported without pulling in the map renderer.

// The `spatial` value can arrive as a GeoJSON object or as a JSON string, and
// may be a bare geometry, a Feature, or a FeatureCollection. Returns a usable
// geometry, or null if nothing parses.
export const parseGeometry = (spatial) => {
  let value = spatial;
  if (typeof value === 'string') {
    try {
      value = JSON.parse(value);
    } catch {
      return null;
    }
  }
  if (!value || typeof value !== 'object') return null;
  if (value.type === 'Feature') return value.geometry || null;
  if (value.type === 'FeatureCollection') {
    const geometries = (value.features || [])
      .map((f) => f && f.geometry)
      .filter(Boolean);
    if (!geometries.length) return null;
    return { type: 'GeometryCollection', geometries };
  }
  if (value.type === 'GeometryCollection' && value.geometries) return value;
  if (value.type && value.coordinates) return value;
  return null;
};

// Walk every coordinate pair in a geometry to build a [lng, lat] bounding box.
// Returns null when no finite coordinate is found.
export const boundsFromGeometry = (geometry) => {
  const acc = {
    minLng: Infinity,
    maxLng: -Infinity,
    minLat: Infinity,
    maxLat: -Infinity
  };

  const collect = (geom) => {
    if (!geom) return;
    if (geom.type === 'GeometryCollection') {
      (geom.geometries || []).forEach(collect);
      return;
    }
    const walk = (coords) => {
      if (!Array.isArray(coords)) return;
      if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
        const [lng, lat] = coords;
        acc.minLng = Math.min(acc.minLng, lng);
        acc.maxLng = Math.max(acc.maxLng, lng);
        acc.minLat = Math.min(acc.minLat, lat);
        acc.maxLat = Math.max(acc.maxLat, lat);
        return;
      }
      coords.forEach(walk);
    };
    walk(geom.coordinates);
  };

  collect(geometry);
  if (!Number.isFinite(acc.minLat) || !Number.isFinite(acc.minLng)) return null;
  return acc;
};
