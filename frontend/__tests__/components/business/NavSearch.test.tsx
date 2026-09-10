import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NavSearch } from '@/components/NavSearch';

jest.mock('next/navigation', () => {
  const push = jest.fn();
  const router = {
    push,
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  };
  return {
    useRouter: jest.fn(() => router),
    usePathname: jest.fn(() => '/'),
    useSearchParams: jest.fn(() => new URLSearchParams()),
    __router: router,
  };
});

const nav = jest.requireMock('next/navigation') as { __router: { push: jest.Mock } };
const pushMock = nav.__router.push;
const HISTORY_KEY = 'nav-search-history';

describe('NavSearch', () => {
  beforeEach(() => {
    localStorage.clear();
    pushMock.mockClear();
  });

  it('renders the search input with a placeholder', () => {
    render(<NavSearch />);
    expect(screen.getByPlaceholderText(/搜索功能/)).toBeInTheDocument();
  });

  it('filters navigation items as the user types and shows the href', async () => {
    const user = userEvent.setup();
    render(<NavSearch />);

    await user.type(screen.getByPlaceholderText(/搜索功能/), 'dashboard');

    expect(await screen.findByText('/dashboard')).toBeInTheDocument();
    expect(screen.getByText('仪表盘')).toBeInTheDocument();
  });

  it('shows the empty-state message when nothing matches', async () => {
    const user = userEvent.setup();
    render(<NavSearch />);

    await user.type(screen.getByPlaceholderText(/搜索功能/), 'zzz-no-match');

    expect(await screen.findByText('未找到匹配的功能')).toBeInTheDocument();
  });

  it('navigates to the item and clears the query when a result is clicked', async () => {
    const user = userEvent.setup();
    render(<NavSearch />);

    await user.type(screen.getByPlaceholderText(/搜索功能/), 'alerts');
    await user.click(await screen.findByRole('button', { name: /告警中心/ }));

    expect(pushMock).toHaveBeenCalledWith('/alerts');
    expect(screen.getByPlaceholderText(/搜索功能/)).toHaveValue('');
  });

  it('persists the query into search history when a result is clicked', async () => {
    const user = userEvent.setup();
    render(<NavSearch />);

    await user.type(screen.getByPlaceholderText(/搜索功能/), 'alerts');
    await user.click(await screen.findByRole('button', { name: /告警中心/ }));

    expect(JSON.parse(localStorage.getItem(HISTORY_KEY) as string)).toContain('alerts');
  });

  it('loads and displays the search history on focus', async () => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(['alerts', 'dashboard']));
    const user = userEvent.setup();
    render(<NavSearch />);

    await user.click(screen.getByPlaceholderText(/搜索功能/));

    expect(await screen.findByText('搜索历史')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'alerts' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'dashboard' })).toBeInTheDocument();
  });

  it('re-runs the search when a history entry is clicked', async () => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(['alerts']));
    const user = userEvent.setup();
    render(<NavSearch />);

    await user.click(screen.getByPlaceholderText(/搜索功能/));
    await user.click(await screen.findByRole('button', { name: 'alerts' }));

    expect(await screen.findByText('/alerts')).toBeInTheDocument();
  });

  it('clears the search history', async () => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(['alerts']));
    const user = userEvent.setup();
    render(<NavSearch />);

    await user.click(screen.getByPlaceholderText(/搜索功能/));
    await user.click(await screen.findByRole('button', { name: '清除' }));

    expect(localStorage.getItem(HISTORY_KEY)).toBeNull();
    await waitFor(() => expect(screen.queryByText('搜索历史')).not.toBeInTheDocument());
  });

  it('tolerates malformed history stored in localStorage', async () => {
    localStorage.setItem(HISTORY_KEY, 'not-json');
    const user = userEvent.setup();
    render(<NavSearch />);

    await user.click(screen.getByPlaceholderText(/搜索功能/));

    expect(screen.queryByText('搜索历史')).not.toBeInTheDocument();
  });

  it('opens with Ctrl+K and closes with Escape', async () => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(['dashboard']));
    render(<NavSearch />);

    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    expect(await screen.findByText('搜索历史')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByText('搜索历史')).not.toBeInTheDocument());
  });

  it('closes when clicking outside the container', async () => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(['dashboard']));
    const user = userEvent.setup();
    render(<NavSearch />);

    await user.click(screen.getByPlaceholderText(/搜索功能/));
    expect(await screen.findByText('搜索历史')).toBeInTheDocument();

    fireEvent.mouseDown(document.body);
    await waitFor(() => expect(screen.queryByText('搜索历史')).not.toBeInTheDocument());
  });
});
