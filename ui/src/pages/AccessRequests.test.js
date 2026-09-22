import React from 'react';
import { render, screen } from '@testing-library/react';
import AccessRequests from './AccessRequests';
import { accessRequestsAPI } from '../services/api';

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

// The API module pulls in axios, which CRA's jest does not transform.
jest.mock('../services/api', () => ({
  accessRequestsAPI: { list: jest.fn() },
}));

const renderPage = () =>
  render(<AccessRequests />);

describe('AccessRequests page', () => {
  afterEach(() => {
    jest.clearAllMocks();
    delete window.__EP_CONFIG__;
  });

  describe('when the workflow is disabled (503)', () => {
    beforeEach(() => {
      accessRequestsAPI.list.mockRejectedValue({ response: { status: 503 } });
    });

    // The bug this guards (issue #270): a switched-off workflow rendered
    // as a red error, which an administrator read as part of an unrelated
    // access problem.
    it('explains the setting instead of reporting an error', async () => {
      renderPage();

      expect(
        await screen.findByText('Access requests are turned off on this endpoint')
      ).toBeInTheDocument();
      expect(screen.getByText('ENABLE_ACCESS_REQUESTS=True')).toBeInTheDocument();
      expect(
        screen.queryByText(/disabled on this deployment/)
      ).not.toBeInTheDocument();
    });

    it('drops the tabs and Refresh, which describe a list that cannot exist', async () => {
      renderPage();
      await screen.findByText('Access requests are turned off on this endpoint');

      expect(screen.queryByRole('button', { name: 'Pending' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Refresh/ })).not.toBeInTheDocument();
    });

    it('names the endpoint group when the endpoint UUID is known', async () => {
      window.__EP_CONFIG__ = { affinitiesEpUuid: '6a4bd301-ab' };
      renderPage();

      expect(await screen.findByText('6a4bd301-ab')).toBeInTheDocument();
    });
  });

  it('still reports a real failure as an error', async () => {
    accessRequestsAPI.list.mockRejectedValue({
      response: { status: 403, data: {} },
    });
    renderPage();

    expect(
      await screen.findByText('Administrator role required to view this page.')
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Access requests are turned off on this endpoint')
    ).not.toBeInTheDocument();
  });

  it('shows the tabs when the workflow is enabled', async () => {
    accessRequestsAPI.list.mockResolvedValue({ data: [] });
    renderPage();

    expect(await screen.findByRole('button', { name: 'Pending' })).toBeInTheDocument();
    expect(
      screen.queryByText('Access requests are turned off on this endpoint')
    ).not.toBeInTheDocument();
  });
});
