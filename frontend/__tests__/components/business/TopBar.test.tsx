import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LocaleProvider } from '@/lib/i18n';
import { TopBar } from '@/components/TopBar';

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  })),
  usePathname: jest.fn(() => '/'),
  useSearchParams: jest.fn(() => new URLSearchParams()),
}));

const renderTopBar = () =>
  render(
    <LocaleProvider>
      <TopBar />
    </LocaleProvider>
  );

describe('TopBar', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders the brand name and embedded nav search', () => {
    renderTopBar();
    expect(screen.getByText('AIOps Agent')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/搜索功能/)).toBeInTheDocument();
  });

  it('renders the language label and locale toggle buttons with the default active', () => {
    renderTopBar();

    expect(screen.getByText('语言')).toBeInTheDocument();
    const zh = screen.getByRole('button', { name: '中' });
    const en = screen.getByRole('button', { name: 'EN' });
    expect(zh).toHaveAttribute('aria-pressed', 'true');
    expect(en).toHaveAttribute('aria-pressed', 'false');
  });

  it('switches the locale when a language button is clicked', async () => {
    const user = userEvent.setup();
    renderTopBar();

    await user.click(screen.getByRole('button', { name: 'EN' }));

    expect(screen.getByText('Language')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'EN' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '中' })).toHaveAttribute('aria-pressed', 'false');
    // Brand name is language-independent.
    expect(screen.getByText('AIOps Agent')).toBeInTheDocument();
  });
});
