import React from 'react';
import { render, screen } from '@testing-library/react';
import DatasetMetadata from './DatasetMetadata';
import { parseGeometry } from './spatialGeometry';

// SpatialMap pulls in Leaflet (ESM, DOM/canvas), which CRA's jest does not
// transform, so the renderer is mocked. The pure geometry logic lives in
// ./spatialGeometry and is imported directly. These tests cover the
// presentation logic: labels, grouping, and the spatial-extent fallback.
jest.mock('./SpatialMap', () => ({
  __esModule: true,
  default: () => <div data-testid="spatial-map">map</div>
}));

const POLYGON = JSON.stringify({
  type: 'Polygon',
  coordinates: [
    [
      [-124.6, 32.3],
      [-113.7, 32.3],
      [-113.7, 42.3],
      [-124.6, 42.3],
      [-124.6, 32.3]
    ]
  ]
});

describe('DatasetMetadata', () => {
  it('renders the map and hides the raw spatial string when geometry parses', () => {
    render(<DatasetMetadata extras={{ spatial: POLYGON, resolution: '10m' }} />);
    expect(screen.getByTestId('spatial-map')).toBeInTheDocument();
    expect(screen.queryByText('Spatial', { exact: false })).toBeInTheDocument();
    // The raw coordinate JSON must not appear as a plain field value.
    expect(screen.queryByText(/coordinates/)).not.toBeInTheDocument();
  });

  it('applies friendly labels to known keys', () => {
    render(<DatasetMetadata extras={{ data_vintage: '2022-2023', EPSG: '4326' }} />);
    expect(screen.getByText('Data vintage')).toBeInTheDocument();
    expect(screen.getByText('EPSG')).toBeInTheDocument();
  });

  it('groups harvest_* fields under a provenance subsection', () => {
    render(
      <DatasetMetadata
        extras={{
          resolution: '10m',
          harvest_source_title: 'WIFIRE Commons',
          harvest_object_id: 'ed2c0667-68b2-499d-a4f0-e2375f7f3975'
        }}
      />
    );
    expect(screen.getByText('Harvest provenance')).toBeInTheDocument();
    expect(screen.getByText('Harvest source')).toBeInTheDocument();
    expect(screen.getByText('WIFIRE Commons')).toBeInTheDocument();
  });

  it('keeps the spatial value as a plain field when it cannot be parsed', () => {
    render(<DatasetMetadata extras={{ spatial: 'not-geojson' }} />);
    expect(screen.queryByTestId('spatial-map')).not.toBeInTheDocument();
    expect(screen.getByText('not-geojson')).toBeInTheDocument();
  });

  it('renders nothing when there are no extras', () => {
    const { container } = render(<DatasetMetadata extras={{}} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('parseGeometry', () => {
  it('parses a JSON string polygon', () => {
    expect(parseGeometry(POLYGON)).toMatchObject({ type: 'Polygon' });
  });

  it('unwraps a Feature into its geometry', () => {
    const feature = { type: 'Feature', geometry: { type: 'Point', coordinates: [1, 2] } };
    expect(parseGeometry(feature)).toMatchObject({ type: 'Point' });
  });

  it('returns null for non-geometry input', () => {
    expect(parseGeometry('nonsense')).toBeNull();
    expect(parseGeometry(null)).toBeNull();
    expect(parseGeometry({ foo: 'bar' })).toBeNull();
  });
});
