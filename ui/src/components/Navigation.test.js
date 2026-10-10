import React from 'react';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import Navigation from './Navigation';
import { statusAPI, userAPI } from '../services/api';

// react-router-dom 7 declares a "main" file it does not ship and relies on
// "exports", which CRA's jest resolver does not understand, so the module
// cannot be loaded here at all. A virtual mock stands in for the two pieces
// these components use.
jest.mock(
  'react-router-dom',
  () => ({
    Link: ({ to, children, ...rest }) => (
      <a href={to} {...rest}>
        {children}
      </a>
    ),
    useNavigate: () => jest.fn(),
  }),
  { virtual: true }
);

// The API module pulls in axios, which CRA's jest does not transform, so it
// is replaced wholesale. The role check is the real one, so these tests
// exercise the same admin rule the app uses.
jest.mock('../services/api', () => ({
  statusAPI: { getStatus: jest.fn() },
  userAPI: { getUserInfo: jest.fn() },
  isAccessRequestAdmin: jest.requireActual('../services/roles')
    .isAccessRequestAdmin,
}));

const renderAs = ({ role, accessRequestsEnabled }) => {
  userAPI.getUserInfo.mockResolvedValue({ data: { effective_role: role } });
  statusAPI.getStatus.mockResolvedValue({
    data: { access_requests_enabled: accessRequestsEnabled },
  });
  render(<Navigation />);
};

// Settle both effects before asserting an absence, so a hidden entry is not
// just one that has not rendered yet. Waiting for the calls is not enough:
// the state is only set in their .then handlers, so the assertion could run
// first and pass even against the old code. Awaiting the same promises the
// component received runs those handlers before this resolves.
const settle = async () => {
  await waitFor(() => {
    expect(userAPI.getUserInfo).toHaveBeenCalled();
    expect(statusAPI.getStatus).toHaveBeenCalled();
  });
  await act(async () => {
    await userAPI.getUserInfo.mock.results[0].value;
    await statusAPI.getStatus.mock.results[0].value;
  });
};

describe('Access Requests navigation entry', () => {
  afterEach(() => jest.clearAllMocks());

  // The bug this guards (issue #270): the entry was shown to every admin,
  // and on endpoints with the workflow off it led to a page that could only
  // show an error.
  it('is shown to an admin when the workflow is enabled', async () => {
    renderAs({ role: 'admin', accessRequestsEnabled: true });

    expect(await screen.findByText('Access Requests')).toBeInTheDocument();
  });

  it('is hidden from an admin when the workflow is disabled', async () => {
    renderAs({ role: 'admin', accessRequestsEnabled: false });
    await settle();

    expect(screen.queryByText('Access Requests')).not.toBeInTheDocument();
  });

  it('is hidden when the status does not report the flag', async () => {
    renderAs({ role: 'admin', accessRequestsEnabled: undefined });
    await settle();

    expect(screen.queryByText('Access Requests')).not.toBeInTheDocument();
  });

  it('stays hidden from a non-admin even when enabled', async () => {
    renderAs({ role: 'writer', accessRequestsEnabled: true });
    await settle();

    expect(screen.queryByText('Access Requests')).not.toBeInTheDocument();
  });
});

describe('"+ New → Kafka topic" entry', () => {
  afterEach(() => jest.clearAllMocks());

  // POST /kafka, the route the Kafka form calls, is only mounted with a local
  // catalog. The entry was shown whenever Kafka was enabled, so on an Endpoint
  // without a local catalog it led to a form whose request could only fail
  // (issue #346).
  const renderWriter = (status) => {
    userAPI.getUserInfo.mockResolvedValue({
      data: { effective_role: 'writer' },
    });
    statusAPI.getStatus.mockResolvedValue({ data: status });
    render(<Navigation />);
  };

  const openNewMenu = async () => {
    const button = await screen.findByText('New');
    fireEvent.mouseEnter(button.closest('div'));
  };

  it('is shown when Kafka is enabled and there is a local catalog', async () => {
    renderWriter({ kafka_enabled: true, local_catalog_backend: 'mongodb' });
    await settle();
    await openNewMenu();

    expect(screen.getByText('Kafka topic')).toBeInTheDocument();
  });

  it('is hidden when there is no local catalog', async () => {
    renderWriter({
      kafka_enabled: true,
      s3_enabled: true,
      local_catalog_backend: 'none',
    });
    await settle();
    await openNewMenu();

    expect(screen.getByText('S3 storage')).toBeInTheDocument();
    expect(screen.queryByText('Kafka topic')).not.toBeInTheDocument();
  });

  it('does not open an empty "+ New" menu on Kafka alone', async () => {
    renderWriter({ kafka_enabled: true, local_catalog_backend: 'none' });
    await settle();

    expect(screen.queryByText('New')).not.toBeInTheDocument();
  });
});
