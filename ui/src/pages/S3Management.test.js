import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import S3Management from './S3Management';
import { s3BucketAPI, s3ObjectAPI, statusAPI, userAPI } from '../services/api';

// Writing to S3 needs the Endpoint's admin tier since 1.0.0; the page shows
// the write controls only to admins and a read-only view to everyone else
// (#399).

jest.mock(
  'react-router-dom',
  () => ({ Navigate: () => null }),
  { virtual: true }
);

// The API module pulls in axios, which CRA's jest does not transform.
jest.mock('../services/api', () => ({
  isAccessRequestAdmin: (info) => info?.effective_role === 'admin',
  statusAPI: { getStatus: jest.fn() },
  userAPI: { getUserInfo: jest.fn() },
  s3BucketAPI: { list: jest.fn(), create: jest.fn(), delete: jest.fn() },
  s3ObjectAPI: { list: jest.fn(), upload: jest.fn(), delete: jest.fn() },
  s3PresignedAPI: { getDownloadUrl: jest.fn(), getUploadUrl: jest.fn() },
}));

const renderAs = async (role) => {
  statusAPI.getStatus.mockResolvedValue({
    data: { s3_enabled: true, api_version: '1.0.0', local_catalog_backend: 'none' },
  });
  userAPI.getUserInfo.mockResolvedValue({ data: { effective_role: role } });
  s3BucketAPI.list.mockResolvedValue({
    data: { buckets: [{ name: 'glsr', creation_date: '2026-11-01T00:00:00Z' }] },
  });
  s3ObjectAPI.list.mockResolvedValue({ data: { objects: [] } });
  render(<S3Management />);
  await screen.findByText('glsr');
  await waitFor(() => expect(userAPI.getUserInfo).toHaveBeenCalled());
};

afterEach(() => jest.clearAllMocks());

test('an admin sees the create and delete controls', async () => {
  await renderAs('admin');

  await screen.findByRole('button', { name: /Create Bucket/ });
  expect(screen.getByTitle('Delete bucket')).toBeInTheDocument();
  expect(screen.queryByText(/^Read-only/)).toBeNull();
});

test.each(['writer', 'viewer', 'none'])(
  'a %s gets a read-only view',
  async (role) => {
    await renderAs(role);

    await screen.findByText(/^Read-only/);
    expect(screen.queryByRole('button', { name: /Create Bucket/ })).toBeNull();
    expect(screen.queryByTitle('Delete bucket')).toBeNull();
    // Reading stays: the bucket can still be selected.
    expect(screen.getByTitle('Select bucket')).toBeInTheDocument();
  }
);

test('when the role cannot be read, the view is read-only', async () => {
  statusAPI.getStatus.mockResolvedValue({ data: { s3_enabled: true } });
  userAPI.getUserInfo.mockRejectedValue(new Error('down'));
  s3BucketAPI.list.mockResolvedValue({ data: { buckets: [] } });
  render(<S3Management />);

  await screen.findByText(/^Read-only/);
  expect(screen.queryByRole('button', { name: /Create Bucket/ })).toBeNull();
});
