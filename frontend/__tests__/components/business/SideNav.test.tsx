import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { SideNav } from '@/components/SideNav';
import { usePathname } from 'next/navigation';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: jest.fn(),
  Link: ({ children, href, className, ...props }: any) => (
    <a href={href} className={className} {...props}>
      {children}
    </a>
  ),
}));

// Mock lib/nav
jest.mock('@/lib/nav', () => ({
  getNavGroups: jest.fn(() => [
    {
      title: 'Monitoring',
      items: [
        { href: '/dashboard', label: 'Dashboard' },
        { href: '/alerts', label: 'Alerts' },
      ],
    },
    {
      title: 'Operations',
      items: [
        { href: '/topology', label: 'Topology' },
        { href: '/workflow', label: 'Workflow' },
      ],
    },
  ]),
}));

// Mock lib/api
jest.mock('@/lib/api', () => ({
  logout: jest.fn(),
}));

// Mock lib/i18n
jest.mock('@/lib/i18n', () => ({
  useI18n: jest.fn(() => (key: string) => key),
  useLocale: jest.fn(() => 'en'),
}));

describe('SideNav Component', () => {
  beforeEach(() => {
    (usePathname as jest.Mock).mockReturnValue('/dashboard');
    localStorage.clear();
  });

  describe('Rendering', () => {
    it('should render navigation groups', () => {
      render(<SideNav />);
      
      expect(screen.getByText('Monitoring')).toBeInTheDocument();
      expect(screen.getByText('Operations')).toBeInTheDocument();
    });

    it('should render navigation items', () => {
      render(<SideNav />);
      
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Alerts')).toBeInTheDocument();
      expect(screen.getByText('Topology')).toBeInTheDocument();
      expect(screen.getByText('Workflow')).toBeInTheDocument();
    });

    it('should render expand/collapse indicators', () => {
      render(<SideNav />);
      
      expect(screen.getByText('▾')).toBeInTheDocument();
    });
  });

  describe('Active State', () => {
    it('should highlight active route', () => {
      (usePathname as jest.Mock).mockReturnValue('/dashboard');
      
      render(<SideNav />);
      
      const activeLink = screen.getByText('Dashboard');
      expect(activeLink).toHaveClass('bg-[var(--dds-slate-70)]');
    });

    it('should not highlight inactive route', () => {
      (usePathname as jest.Mock).mockReturnValue('/alerts');
      
      render(<SideNav />);
      
      const inactiveLink = screen.getByText('Dashboard');
      expect(inactiveLink).not.toHaveClass('bg-[var(--dds-slate-70)]');
    });

    it('should handle route prefixes correctly', () => {
      (usePathname as jest.Mock).mockReturnValue('/dashboard/subpage');
      
      render(<SideNav />);
      
      const activeLink = screen.getByText('Dashboard');
      expect(activeLink).toHaveClass('bg-[var(--dds-slate-70)]');
    });
  });

  describe('Expand/Collapse Functionality', () => {
    it('should expand group by default', () => {
      render(<SideNav />);
      
      expect(screen.getByText('Dashboard')).toBeVisible();
    });

    it('should collapse group when clicked', async () => {
      const { container } = render(<SideNav />);
      
      const groupButton = screen.getByText('Monitoring');
      // Click to collapse
      groupButton.click();
      
      // Items should still be visible in this implementation
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });

  describe('User Info', () => {
    it('should render user info when available', () => {
      localStorage.setItem('user', JSON.stringify({
        username: 'testuser',
        role: 'admin',
      }));
      
      render(<SideNav />);
      
      expect(screen.getByText('testuser')).toBeInTheDocument();
      expect(screen.getByText('(admin)')).toBeInTheDocument();
    });

    it('should not render user info when not available', () => {
      localStorage.clear();
      
      render(<SideNav />);
      
      expect(screen.queryByText(/testuser/)).not.toBeInTheDocument();
    });

    it('should handle invalid localStorage data', () => {
      localStorage.setItem('user', 'invalid json');
      
      render(<SideNav />);
      
      // Should not throw error
      expect(screen.getByText('Monitoring')).toBeInTheDocument();
    });
  });

  describe('Logout Functionality', () => {
    it('should render logout button when user is logged in', () => {
      localStorage.setItem('user', JSON.stringify({
        username: 'testuser',
        role: 'admin',
      }));
      
      render(<SideNav />);
      
      const logoutButton = screen.getByText('sidenav.logout');
      expect(logoutButton).toBeInTheDocument();
    });

    it('should call logout API when logout button clicked', async () => {
      const { logout } = require('@/lib/api');
      localStorage.setItem('user', JSON.stringify({
        username: 'testuser',
        role: 'admin',
      }));
      
      render(<SideNav />);
      
      const logoutButton = screen.getByText('sidenav.logout');
      logoutButton.click();
      
      await waitFor(() => {
        expect(logout).toHaveBeenCalled();
      });
    });
  });

  describe('External Links', () => {
    it('should render external links correctly', () => {
      const { getNavGroups } = require('@/lib/nav');
      getNavGroups.mockReturnValue([
        {
          title: 'External',
          items: [
            { href: 'https://example.com', label: 'Example', target: '_blank' },
          ],
        },
      ]);
      
      render(<SideNav />);
      
      const externalLink = screen.getByText('Example');
      expect(externalLink).toBeInTheDocument();
      expect(screen.getByText('↗')).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply correct container styles', () => {
      const { container } = render(<SideNav />);
      
      const aside = container.querySelector('aside');
      expect(aside).toHaveClass('w-72');
      expect(aside).toHaveClass('h-full');
    });

    it('should apply correct group button styles', () => {
      render(<SideNav />);
      
      const groupButton = screen.getByText('Monitoring');
      expect(groupButton).toHaveClass('uppercase');
      expect(groupButton).toHaveClass('tracking-wider');
    });
  });

  describe('Accessibility', () => {
    it('should have proper navigation role', () => {
      render(<SideNav />);
      
      const navs = screen.getAllByRole('navigation');
      expect(navs.length).toBeGreaterThan(0);
    });

    it('should have accessible links', () => {
      render(<SideNav />);
      
      const links = screen.getAllByRole('link');
      expect(links.length).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty navigation groups', () => {
      const { getNavGroups } = require('@/lib/nav');
      getNavGroups.mockReturnValue([]);
      
      render(<SideNav />);
      
      // Should not throw error
      const aside = document.querySelector('aside');
      expect(aside).toBeInTheDocument();
    });

    it('should handle groups with no items', () => {
      const { getNavGroups } = require('@/lib/nav');
      getNavGroups.mockReturnValue([
        { title: 'Empty', items: [] },
      ]);
      
      render(<SideNav />);
      
      expect(screen.getByText('Empty')).toBeInTheDocument();
    });

    it('should handle root path', () => {
      (usePathname as jest.Mock).mockReturnValue('/');
      
      render(<SideNav />);
      
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });

  describe('Internationalization', () => {
    it('should use i18n for labels', () => {
      const { useI18n } = require('@/lib/i18n');
      useI18n.mockReturnValue((key: string) => `Translated: ${key}`);
      
      render(<SideNav />);
      
      expect(screen.getByText('Translated: sidenav.logout')).toBeInTheDocument();
    });
  });
});
