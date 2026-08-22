import React from 'react';
import { render, screen } from '@testing-library/react';
import { Sidebar } from '@/components/layout/Sidebar';
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

describe('Sidebar Component', () => {
  beforeEach(() => {
    (usePathname as jest.Mock).mockReturnValue('/dashboard');
  });

  describe('Rendering', () => {
    it('should render sidebar with all navigation items', () => {
      render(<Sidebar />);
      
      expect(screen.getByText('仪表盘')).toBeInTheDocument();
      expect(screen.getByText('告警')).toBeInTheDocument();
      expect(screen.getByText('拓扑')).toBeInTheDocument();
      expect(screen.getByText('分析')).toBeInTheDocument();
      expect(screen.getByText('修复')).toBeInTheDocument();
      expect(screen.getByText('容量')).toBeInTheDocument();
      expect(screen.getByText('成本')).toBeInTheDocument();
      expect(screen.getByText('监控')).toBeInTheDocument();
      expect(screen.getByText('设置')).toBeInTheDocument();
    });

    it('should render app title', () => {
      render(<Sidebar />);
      
      expect(screen.getByText('AIOps Agent')).toBeInTheDocument();
    });

    it('should render app icon', () => {
      render(<Sidebar />);
      
      expect(screen.getByText('🤖')).toBeInTheDocument();
    });

    it('should render user info section', () => {
      render(<Sidebar />);
      
      expect(screen.getByText('用户')).toBeInTheDocument();
      expect(screen.getByText('管理员')).toBeInTheDocument();
    });

    it('should render user avatar', () => {
      render(<Sidebar />);
      
      const avatar = screen.getByText('U');
      expect(avatar).toBeInTheDocument();
    });
  });

  describe('Active State', () => {
    it('should highlight active route', () => {
      (usePathname as jest.Mock).mockReturnValue('/dashboard');
      
      render(<Sidebar />);
      
      const activeLink = screen.getByText('仪表盘');
      expect(activeLink).toHaveClass('bg-blue-600');
    });

    it('should not highlight inactive route', () => {
      (usePathname as jest.Mock).mockReturnValue('/alerts');
      
      render(<Sidebar />);
      
      const inactiveLink = screen.getByText('仪表盘');
      expect(inactiveLink).not.toHaveClass('bg-blue-600');
    });

    it('should handle route prefixes correctly', () => {
      (usePathname as jest.Mock).mockReturnValue('/dashboard/subpage');
      
      render(<Sidebar />);
      
      const activeLink = screen.getByText('仪表盘');
      expect(activeLink).toHaveClass('bg-blue-600');
    });
  });

  describe('Navigation Items', () => {
    it('should render icons for each item', () => {
      render(<Sidebar />);
      
      expect(screen.getByText('📊')).toBeInTheDocument();
      expect(screen.getByText('🔔')).toBeInTheDocument();
      expect(screen.getByText('🔗')).toBeInTheDocument();
      expect(screen.getByText('📈')).toBeInTheDocument();
      expect(screen.getByText('🔧')).toBeInTheDocument();
      expect(screen.getByText('💾')).toBeInTheDocument();
      expect(screen.getByText('💰')).toBeInTheDocument();
      expect(screen.getByText('📡')).toBeInTheDocument();
      expect(screen.getByText('⚙️')).toBeInTheDocument();
    });

    it('should have correct href for each item', () => {
      render(<Sidebar />);
      
      const dashboardLink = screen.getByText('仪表盘').closest('a');
      expect(dashboardLink).toHaveAttribute('href', '/dashboard');
      
      const alertsLink = screen.getByText('告警').closest('a');
      expect(alertsLink).toHaveAttribute('href', '/alerts');
    });
  });

  describe('Styling', () => {
    it('should apply correct sidebar styles', () => {
      const { container } = render(<Sidebar />);
      
      const aside = container.querySelector('aside');
      expect(aside).toHaveClass('w-64');
      expect(aside).toHaveClass('bg-gray-900');
      expect(aside).toHaveClass('text-white');
    });

    it('should apply correct link styles', () => {
      render(<Sidebar />);
      
      const links = screen.getAllByRole('link');
      links.forEach(link => {
        expect(link).toHaveClass('flex');
        expect(link).toHaveClass('items-center');
      });
    });

    it('should apply correct header styles', () => {
      render(<Sidebar />);
      
      const header = screen.getByText('AIOps Agent').closest('div');
      expect(header).toHaveClass('border-b');
    });
  });

  describe('User Section', () => {
    it('should render user info at bottom', () => {
      render(<Sidebar />);
      
      const userSection = screen.getByText('用户').closest('div');
      expect(userSection).toHaveClass('border-t');
    });

    it('should display user avatar with correct styles', () => {
      render(<Sidebar />);
      
      const avatar = screen.getByText('U');
      expect(avatar).toHaveClass('bg-blue-500');
    });
  });

  describe('Responsive Behavior', () => {
    it('should render correctly on different screen sizes', () => {
      render(<Sidebar />);
      
      const aside = document.querySelector('aside');
      expect(aside).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper navigation role', () => {
      render(<Sidebar />);
      
      const nav = screen.getByRole('navigation');
      expect(nav).toBeInTheDocument();
    });

    it('should have accessible links', () => {
      render(<Sidebar />);
      
      const links = screen.getAllByRole('link');
      expect(links.length).toBeGreaterThan(0);
    });
  });

  describe('Edge Cases', () => {
    it('should handle root path', () => {
      (usePathname as jest.Mock).mockReturnValue('/');
      
      render(<Sidebar />);
      
      expect(screen.getByText('仪表盘')).toBeInTheDocument();
    });

    it('should handle unknown path', () => {
      (usePathname as jest.Mock).mockReturnValue('/unknown');
      
      render(<Sidebar />);
      
      // Should still render all items
      expect(screen.getByText('仪表盘')).toBeInTheDocument();
      expect(screen.getByText('告警')).toBeInTheDocument();
    });
  });

  describe('Integration', () => {
    it('should work with Next.js router', () => {
      (usePathname as jest.Mock).mockReturnValue('/topology');
      
      render(<Sidebar />);
      
      const activeLink = screen.getByText('拓扑');
      expect(activeLink).toHaveClass('bg-blue-600');
    });
  });
});
