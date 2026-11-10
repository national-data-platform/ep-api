import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import StacCollectionSummary, {
  bboxToGeometry,
  looksLikeStacCollection,
  periodLabel
} from './StacCollectionSummary';
import { stacAPI } from '../services/api';

// Leaflet is not transformed by CRA's jest; see DatasetMetadata.test.js.
jest.mock('./SpatialMap', () => ({
  __esModule: true,
  default: () => <div data-testid="spatial-map">map</div>
}));

jest.mock('../services/api', () => ({
  stacAPI: { collection: jest.fn(), item: jest.fn() }
}));

const items = [
  'macav2metdata_GSLBIP_ACCESS-CM2_ssp126_1979-1988',
  'macav2metdata_GSLBIP_MIROC6_ssp370_2090-2099',
  'macav2metdata_GSLBIP_MIROC6_ssp126_2090-2099'
].map((id) => ({ id, href: `https://files.example/stac/items/${id}.json` }));

const summary = {
  title: 'MACAv2 Statistically Downscaled CMIP6 — GSLBIP',
  description: 'Great Salt Lake Basin.',
  license: 'other',
  bbox: [-115.1, 36.025, -108.01667, 42.983334],
  interval: ['1979-01-01T00:00:00Z', '2099-12-31T23:59:59Z'],
  summaries: [
    { name: 'model', values: ['ACCESS-CM2', 'MIROC6'], count: 2 },
    { name: 'scenario', values: ['ssp126', 'ssp370'], count: 2 }
  ],
  item_count: 3,
  items
};

describe('looksLikeStacCollection', () => {
  test.each([
    [{ id: 'r', url: 'https://x.org/files/stac/collection.json', format: 'JSON' }, true],
    [{ id: 'r', url: 'https://x.org/catalog', format: 'STAC' }, true],
    [{ id: 'r', url: 'https://x.org/data.nc', format: 'NetCDF' }, false],
    [{ id: 'r', url: 'https://x.org/files/', format: 'HTML' }, false],
    [{ id: 'r', url: 'not a url', format: 'JSON' }, false],
    [{ url: 'https://x.org/collection.json' }, false]
  ])('%o -> %s', (resource, expected) => {
    expect(looksLikeStacCollection(resource)).toBe(expected);
  });
});

test('the bounding box becomes a polygon for the map', () => {
  expect(bboxToGeometry([-115, 36, -108, 43]).coordinates[0][2]).toEqual([-108, 43]);
  expect(bboxToGeometry(null)).toBeNull();
});

test('the period shows the years', () => {
  expect(periodLabel(['1979-01-01T00:00:00Z', '2099-12-31T23:59:59Z'])).toBe('1979–2099');
  expect(periodLabel(['1979-01-01T00:00:00Z', null])).toBe('1979–…');
  expect(periodLabel(null)).toBeNull();
});

describe('StacCollectionSummary', () => {
  beforeEach(() => {
    stacAPI.collection.mockResolvedValue({ data: summary });
    stacAPI.item.mockResolvedValue({
      data: {
        properties: { start_datetime: '2090-01-01T00:00:00Z', end_datetime: '2099-12-31T23:59:59Z' },
        assets: [
          {
            key: 'data',
            title: 'macav2metdata_GSLBIP_MIROC6_ssp370_2090-2099.nc',
            href: 'https://files.example/macav2metdata_GSLBIP_MIROC6_ssp370_2090-2099.nc',
            type: 'application/x-netcdf'
          }
        ]
      }
    });
  });

  afterEach(() => jest.clearAllMocks());

  test('shows the extent, counts and items of the collection', async () => {
    render(<StacCollectionSummary server="global" datasetId="ds-1" resourceId="res-1" />);

    expect(await screen.findByText(summary.title)).toBeInTheDocument();
    expect(stacAPI.collection).toHaveBeenCalledWith('global', 'ds-1', 'res-1');
    expect(screen.getByText('1979–2099')).toBeInTheDocument();
    expect(screen.getByTestId('spatial-map')).toBeInTheDocument();
    expect(screen.getByText(/Showing 3 of 3 items/)).toBeInTheDocument();
  });

  test('filters items by every word typed', async () => {
    render(<StacCollectionSummary server="global" datasetId="ds-1" resourceId="res-1" />);
    await screen.findByText(summary.title);

    fireEvent.change(screen.getByLabelText('Filter items by name'), {
      target: { value: 'miroc6 ssp370' }
    });

    expect(screen.getByText('macav2metdata_GSLBIP_MIROC6_ssp370_2090-2099')).toBeInTheDocument();
    expect(screen.queryByText('macav2metdata_GSLBIP_MIROC6_ssp126_2090-2099')).not.toBeInTheDocument();
    expect(screen.getByText(/Showing 1 of 1 matching items/)).toBeInTheDocument();
  });

  test('opening an item asks for it once and shows its download link', async () => {
    render(<StacCollectionSummary server="global" datasetId="ds-1" resourceId="res-1" />);
    await screen.findByText(summary.title);

    fireEvent.click(screen.getByText('macav2metdata_GSLBIP_MIROC6_ssp370_2090-2099'));

    const link = await screen.findByRole('link', {
      name: /macav2metdata_GSLBIP_MIROC6_ssp370_2090-2099\.nc/
    });
    expect(link).toHaveAttribute(
      'href',
      'https://files.example/macav2metdata_GSLBIP_MIROC6_ssp370_2090-2099.nc'
    );
    expect(stacAPI.item).toHaveBeenCalledWith('global', 'ds-1', 'res-1', items[1].href);
    expect(stacAPI.item).toHaveBeenCalledTimes(1);
  });

  test('says why when the collection cannot be read', async () => {
    stacAPI.collection.mockRejectedValue({
      response: { data: { detail: 'This resource is not a STAC collection.' } }
    });

    render(<StacCollectionSummary server="local" datasetId="ds-1" resourceId="res-1" />);

    expect(await screen.findByText('This resource is not a STAC collection.')).toBeInTheDocument();
  });
});
