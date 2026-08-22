import React from 'react';
import { render, screen } from '@testing-library/react';
import { NavBar } from '@/components/NavBar';
import { usePathname } from 'next/navigation';
import { ThemeProvider } from '@/components/ThemeProvider';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: jest.fn(),
  Link: ({ children, href, className, ...props }: any) => (
    <a href={href} className={className} {...props}>
      {children}
    </a>
  ),
}));

// Mock ThemeToggle
jest.mock('@/components/ThemeToggle', () => ({
  ThemeToggle: () => <button>Theme</button>,
}));

describe('NavBar Component', () => {
  beforeEach(() => {
    (usePathname as jest.Mock).mockReturnValue('/overview');
  });

  const renderWithTheme = (component: React.ReactElement) => {
    return render(
      <ThemeProvider>
        {component}
      </ThemeProvider>
    );
  };

  describe('Rendering', () => {
    it('should render all navigation items', () => {
      renderWithTheme(<NavBar />);

      expect(screen.getByText('总览')).toBeInTheDocument();
      expect(screen.getByText('拓扑')).toBeInTheDocument();
      expect(screen.getByText('工作流')).toBeInTheDocument();
      expect(screen.getByText('审批')).toBeInTheDocument();
      expect(screen.getByText('案例')).toBeInTheDocument();
      expect(screen.getByText('审计')).toBeInTheDocument();
    });

    it('should render ThemeToggle component', () => {
      renderWithTheme(<NavBar />);

      // ThemeToggle should be present
      const themeToggle = screen.getByRole('button');
      expect(themeToggle).toBeInTheDocument();
    });
  });

  describe('Active State', () => {
    it('should highlight active route', () => {
      (usePathname as jest.Mock).mockReturnValue('/overview');

      renderWithTheme(<NavBar />);

      const activeLink = screen.getByText('总览');
      expect(activeLink).toHaveClass('bg-primary');
    });

    it('should not highlight inactive route', () => {
      (usePathname as jest.Mock).mockReturnValue('/topology');

      renderWithTheme(<NavBar />);

      const inactiveLink = screen.getByText('总览');
      expect(inactiveLink).not.toHaveClass('bg-primary');
    });

    it('should handle route prefixes correctly', () => {
      (usePathname as jest.Mock).mockReturnValue('/overview/subpage');

      renderWithTheme(<NavBar />);

      const activeLink = screen.getByText('总览');
      expect(activeLink).toHaveClass('bg-primary');
    });
  });

  describe('Styling', () => {
    it('should apply correct container styles', () => {
      const { container } = render(<NavBar />);

      const nav = container.querySelector('nav');
      expect(nav).toHaveClass('bg-gray-100');
      expect(nav).toHaveClass('border-b');
    });

    it('should apply correct link styles', () => {
      renderWithTheme(<NavBar />);

      const links = screen.getAllByRole('link');
      links.forEach(link => {
        expect(link).toHaveClass('px-3');
        expect(link).toHaveClass('py-1');
        expect(link).toHaveClass('rounded');
      });
    });
  });

  describe('Navigation Items', () => {
    it('should have correct href for each item', () => {
      renderWithTheme(<NavBar />);

      const overviewLink = screen.getByText('总览').closest('a');
      expect(overviewLink).toHaveAttribute('href', '/overview');

      const topologyLink = screen.getByText('拓扑').closest('a');
      expect(topologyLink).toHaveAttribute('href', '/topology');
    });
  });

  describe('Responsive Behavior', () => {
    it('should render correctly on different screen sizes', () => {
      renderWithTheme(<NavBar />);

      const nav = screen.getByRole('navigation');
      expect(nav).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper navigation role', () => {
      renderWithTheme(<NavBar />);

      const nav = screen.getByRole('navigation');
      expect(nav).toBeInTheDocument();
    });

    it('should have accessible links', () => {
      renderWithTheme(<NavBar />);

      const links = screen.getAllByRole('link');
      expect(links.length).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases', () => {
    it('should handle root path', () => {
      (usePathname as jest.Mock).mockReturnValue('/');

      renderWithTheme(<NavBar />);

      expect(screen.getByText('总览')).toBeInTheDocument();
    });

    it('should handle unknown path', () => {
      (usePathname as jest.Mock).mockReturnValue('/unknown');

      renderWithTheme(<NavBar />);

      // Should still render all items
      expect(screen.getByText('总览')).toBeInTheDocument();
      expect(screen.getByText('拓扑')).toBeInTheDocument();
    });
  });

  describe('Integration', () => {
    it('should work with ThemeProvider', () => {
      // This test verifies NavBar can be used with ThemeProvider
      expect(() => {
        renderWithTheme(<NavBar />);
      }).not.toThrow();
    });
  });
});
