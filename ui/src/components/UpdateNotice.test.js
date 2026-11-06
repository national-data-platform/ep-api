import { render, screen } from '@testing-library/react';
import UpdateNotice from './UpdateNotice';

const newer = {
  current_version: '0.34.71',
  latest_version: '0.35.0',
  update_available: true,
  release_url: 'https://github.com/national-data-platform/ep-api/releases/tag/v0.35.0',
  changelog_url: 'https://github.com/national-data-platform/ep-api/blob/v0.35.0/CHANGELOG.md',
};

describe('UpdateNotice', () => {
  test('shows the latest version and both links when an update is available', () => {
    render(<UpdateNotice info={newer} />);

    expect(screen.getByText(/newer ep-api release is available: 0\.35\.0/)).toBeInTheDocument();
    expect(screen.getByText(/runs 0\.34\.71/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Release notes' })).toHaveAttribute('href', newer.release_url);
    expect(screen.getByRole('link', { name: 'CHANGELOG' })).toHaveAttribute('href', newer.changelog_url);
  });

  test.each([
    ['no answer', null],
    ['up to date', { ...newer, update_available: false }],
    ['latest unknown', { ...newer, latest_version: null, update_available: null }],
  ])('shows nothing when %s', (_label, info) => {
    const { container } = render(<UpdateNotice info={info} />);
    expect(container).toBeEmptyDOMElement();
  });

  test('leaves out a link the backend did not send', () => {
    render(<UpdateNotice info={{ ...newer, changelog_url: null }} />);
    expect(screen.getByRole('link', { name: 'Release notes' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'CHANGELOG' })).toBeNull();
  });
});
