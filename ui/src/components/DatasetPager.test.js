import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import DatasetPager from './DatasetPager';

describe('DatasetPager', () => {
  test('says how many of the matches are shown and loads more on request', () => {
    const onLoadMore = jest.fn();
    render(<DatasetPager shown={100} total={1124} hasMore onLoadMore={onLoadMore} />);

    expect(screen.getByText('Showing 100 of 1124 matching datasets')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Load more' }));
    expect(onLoadMore).toHaveBeenCalledTimes(1);
  });

  test('offers no button once everything is shown', () => {
    render(<DatasetPager shown={370} total={370} hasMore={false} onLoadMore={() => {}} />);

    expect(screen.getByText('Showing 370 of 370 matching datasets')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  test('is disabled while a page is loading', () => {
    render(<DatasetPager shown={100} total={1124} hasMore loading onLoadMore={() => {}} />);

    expect(screen.getByRole('button', { name: 'Loading…' })).toBeDisabled();
  });

  test('with "Only mine" it says how many matches were looked through', () => {
    render(
      <DatasetPager shown={2} total={1124} hasMore onlyMine lookedAt={100} onLoadMore={() => {}} />
    );

    expect(
      screen.getByText('Showing 2 of yours among the first 100 of 1124 matching datasets')
    ).toBeInTheDocument();
  });

  test('shows nothing without a total', () => {
    const { container } = render(
      <DatasetPager shown={3} total={null} hasMore={false} onLoadMore={() => {}} />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
