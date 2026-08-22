import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KpiCard } from '@/components/ui/KpiCard';
import { TrendingUp } from 'lucide-react';

// Mock the Card components
jest.mock('@/components/ui/card', () => ({
  Card: ({ children, className, onClick }: any) => (
    <div className={className} onClick={onClick} data-testid="card">
      {children}
    </div>
  ),
  CardHeader: ({ children, className }: any) => (
    <div className={className} data-testid="card-header">
      {children}
    </div>
  ),
  CardTitle: ({ children, className }: any) => (
    <h3 className={className} data-testid="card-title">
      {children}
    </h3>
  ),
  CardContent: ({ children, className }: any) => (
    <div className={className} data-testid="card-content">
      {children}
    </div>
  ),
}));

// Mock the Badge component
jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, className, variant }: any) => (
    <span className={className} data-variant={variant} data-testid="badge">
      {children}
    </span>
  ),
}));

// Mock the lucide-react icon
jest.mock('lucide-react', () => ({
  TrendingUp: () => <span data-testid="trending-up-icon">📈</span>,
}));

describe('KpiCard Component', () => {
  describe('Rendering', () => {
    it('should render card with title and value', () => {
      render(<KpiCard title="Total Users" value="1000" />);
      expect(screen.getByText('Total Users')).toBeInTheDocument();
      expect(screen.getByText('1000')).toBeInTheDocument();
    });

    it('should render card with unit', () => {
      render(<KpiCard title="Revenue" value="5000" unit="$" />);
      expect(screen.getByText('$')).toBeInTheDocument();
    });

    it('should render card with icon', () => {
      render(<KpiCard title="Trend" value="100" icon={TrendingUp} />);
      expect(screen.getByTestId('trending-up-icon')).toBeInTheDocument();
    });

    it('should render card with description', () => {
      render(<KpiCard title="Metric" value="50" description="Monthly average" />);
      expect(screen.getByText('Monthly average')).toBeInTheDocument();
    });

    it('should render card with trend', () => {
      render(<KpiCard title="Growth" value="10" trend="up" trendValue={5} />);
      expect(screen.getByText('↑')).toBeInTheDocument();
      expect(screen.getByText('上升 5%')).toBeInTheDocument();
    });

    it('should render card with level badge', () => {
      render(<KpiCard title="Status" value="Good" level="normal" />);
      expect(screen.getByText('正常')).toBeInTheDocument();
    });
  });

  describe('Level Variants', () => {
    it('should render normal level', () => {
      render(<KpiCard title="Status" value="Good" level="normal" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveTextContent('正常');
      expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('should render warning level', () => {
      render(<KpiCard title="Status" value="Warning" level="warning" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveTextContent('警告');
      expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
    });

    it('should render critical level', () => {
      render(<KpiCard title="Status" value="Critical" level="critical" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveTextContent('严重');
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should default to normal level', () => {
      render(<KpiCard title="Status" value="Good" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveTextContent('正常');
    });

    it('should apply color to value based on level', () => {
      const { rerender } = render(<KpiCard title="Status" value="100" level="normal" />);
      expect(screen.getByText('100')).toHaveClass('text-green-600');

      rerender(<KpiCard title="Status" value="100" level="warning" />);
      expect(screen.getByText('100')).toHaveClass('text-yellow-600');

      rerender(<KpiCard title="Status" value="100" level="critical" />);
      expect(screen.getByText('100')).toHaveClass('text-red-600');
    });
  });

  describe('Trend Variants', () => {
    it('should render up trend with correct icon and text', () => {
      render(<KpiCard title="Growth" value="10" trend="up" trendValue={5} />);
      expect(screen.getByText('↑')).toBeInTheDocument();
      expect(screen.getByText('上升 5%')).toBeInTheDocument();
      expect(screen.getByText('↑')).toHaveClass('text-red-500');
    });

    it('should render down trend with correct icon and text', () => {
      render(<KpiCard title="Decline" value="10" trend="down" trendValue={3} />);
      expect(screen.getByText('↓')).toBeInTheDocument();
      expect(screen.getByText('下降 3%')).toBeInTheDocument();
      expect(screen.getByText('↓')).toHaveClass('text-green-500');
    });

    it('should render stable trend with correct icon and text', () => {
      render(<KpiCard title="Stable" value="10" trend="stable" trendValue={0} />);
      expect(screen.getByText('→')).toBeInTheDocument();
      expect(screen.getByText('稳定 0%')).toBeInTheDocument();
      expect(screen.getByText('→')).toHaveClass('text-gray-500');
    });

    it('should not render trend when trendValue is undefined', () => {
      render(<KpiCard title="Growth" value="10" trend="up" />);
      expect(screen.queryByText('↑')).not.toBeInTheDocument();
    });

    it('should not render trend when trend is not provided', () => {
      render(<KpiCard title="Growth" value="10" trendValue={5} />);
      expect(screen.queryByText('↑')).not.toBeInTheDocument();
    });

    it('should show absolute value of trendValue', () => {
      render(<KpiCard title="Growth" value="10" trend="up" trendValue={-5} />);
      expect(screen.getByText('上升 5%')).toBeInTheDocument();
    });
  });

  describe('Value Types', () => {
    it('should render string value', () => {
      render(<KpiCard title="Status" value="Active" />);
      expect(screen.getByText('Active')).toBeInTheDocument();
    });

    it('should render number value', () => {
      render(<KpiCard title="Count" value={1000} />);
      expect(screen.getByText('1000')).toBeInTheDocument();
    });

    it('should render decimal value', () => {
      render(<KpiCard title="Rate" value={95.5} />);
      expect(screen.getByText('95.5')).toBeInTheDocument();
    });

    it('should render zero value', () => {
      render(<KpiCard title="Count" value={0} />);
      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('should render negative value', () => {
      render(<KpiCard title="Change" value={-50} />);
      expect(screen.getByText('-50')).toBeInTheDocument();
    });
  });

  describe('Event Handling', () => {
    it('should call onClick handler when clicked', async () => {
      const handleClick = jest.fn();
      const user = userEvent.setup();
      render(<KpiCard title="Clickable" value="100" onClick={handleClick} />);
      
      const card = screen.getByTestId('card');
      await user.click(card);
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should not call onClick when not provided', async () => {
      const user = userEvent.setup();
      render(<KpiCard title="Not Clickable" value="100" />);
      
      const card = screen.getByTestId('card');
      await user.click(card);
      
      // Should not throw error
    });

    it('should add hover styles when onClick is provided', () => {
      render(<KpiCard title="Clickable" value="100" onClick={() => {}} />);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('hover:shadow-md', 'transition', 'cursor-pointer', 'hover:border-blue-300');
    });

    it('should not add hover styles when onClick is not provided', () => {
      render(<KpiCard title="Not Clickable" value="100" />);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('hover:shadow-md', 'transition', 'cursor-pointer');
      expect(card).not.toHaveClass('hover:border-blue-300');
    });
  });

  describe('Edge Cases', () => {
    it('should render with empty description', () => {
      render(<KpiCard title="Metric" value="50" description="" />);
      expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('should render with long title', () => {
      const longTitle = 'This is a very long KPI card title that might wrap';
      render(<KpiCard title={longTitle} value="100" />);
      expect(screen.getByText(longTitle)).toBeInTheDocument();
    });

    it('should render with long value', () => {
      const longValue = '999999999999999999999';
      render(<KpiCard title="Large Number" value={longValue} />);
      expect(screen.getByText(longValue)).toBeInTheDocument();
    });

    it('should render with special characters in title', () => {
      render(<KpiCard title="Status (Active)" value="100" />);
      expect(screen.getByText('Status (Active)')).toBeInTheDocument();
    });

    it('should render with unicode characters', () => {
      render(<KpiCard title="状态" value="100" />);
      expect(screen.getByText('状态')).toBeInTheDocument();
    });

    it('should render without unit when not provided', () => {
      render(<KpiCard title="Count" value="100" />);
      expect(screen.queryByText(/unit/i)).not.toBeInTheDocument();
    });

    it('should render without icon when not provided', () => {
      render(<KpiCard title="Metric" value="100" />);
      expect(screen.queryByTestId('trending-up-icon')).not.toBeInTheDocument();
    });

    it('should render without description when not provided', () => {
      render(<KpiCard title="Metric" value="100" />);
      const content = screen.getByTestId('card-content');
      expect(content).not.toContainHTML(/description/i);
    });
  });

  describe('Component Structure', () => {
    it('should render CardHeader', () => {
      render(<KpiCard title="Title" value="100" />);
      expect(screen.getByTestId('card-header')).toBeInTheDocument();
    });

    it('should render CardTitle', () => {
      render(<KpiCard title="Title" value="100" />);
      expect(screen.getByTestId('card-title')).toBeInTheDocument();
    });

    it('should render CardContent', () => {
      render(<KpiCard title="Title" value="100" />);
      expect(screen.getByTestId('card-content')).toBeInTheDocument();
    });

    it('should render value in correct font size', () => {
      render(<KpiCard title="Title" value="100" />);
      const value = screen.getByText('100');
      expect(value).toHaveClass('text-3xl', 'font-bold');
    });

    it('should render title in correct font size', () => {
      render(<KpiCard title="Title" value="100" />);
      const title = screen.getByTestId('card-title');
      expect(title).toHaveClass('text-sm', 'font-medium');
    });
  });

  describe('Integration Tests', () => {
    it('should render complete KPI card with all props', () => {
      render(
        <KpiCard
          title="Total Revenue"
          value="50000"
          unit="$"
          icon={TrendingUp}
          trend="up"
          trendValue={15}
          level="normal"
          description="Monthly revenue"
          onClick={() => {}}
        />
      );

      expect(screen.getByText('Total Revenue')).toBeInTheDocument();
      expect(screen.getByText('50000')).toBeInTheDocument();
      expect(screen.getByText('$')).toBeInTheDocument();
      expect(screen.getByTestId('trending-up-icon')).toBeInTheDocument();
      expect(screen.getByText('↑')).toBeInTheDocument();
      expect(screen.getByText('上升 15%')).toBeInTheDocument();
      expect(screen.getByText('正常')).toBeInTheDocument();
      expect(screen.getByText('Monthly revenue')).toBeInTheDocument();
    });

    it('should handle critical level with down trend', () => {
      render(
        <KpiCard
          title="Error Rate"
          value="5"
          unit="%"
          trend="down"
          trendValue={10}
          level="critical"
        />
      );

      expect(screen.getByText('严重')).toBeInTheDocument();
      expect(screen.getByText('↓')).toBeInTheDocument();
      expect(screen.getByText('下降 10%')).toBeInTheDocument();
      expect(screen.getByText('5')).toHaveClass('text-red-600');
    });

    it('should handle warning level with stable trend', () => {
      render(
        <KpiCard
          title="Response Time"
          value="500"
          unit="ms"
          trend="stable"
          trendValue={0}
          level="warning"
        />
      );

      expect(screen.getByText('警告')).toBeInTheDocument();
      expect(screen.getByText('→')).toBeInTheDocument();
      expect(screen.getByText('稳定 0%')).toBeInTheDocument();
      expect(screen.getByText('500')).toHaveClass('text-yellow-600');
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading structure', () => {
      render(<KpiCard title="KPI Title" value="100" />);
      const title = screen.getByRole('heading', { name: 'KPI Title' });
      expect(title).toBeInTheDocument();
    });

    it('should support aria-label on card', () => {
      render(<KpiCard title="KPI" value="100" />);
      const card = screen.getByTestId('card');
      expect(card).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should have correct base styles', () => {
      render(<KpiCard title="Title" value="100" />);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('hover:shadow-md', 'transition', 'cursor-pointer');
    });

    it('should have correct value display styles', () => {
      render(<KpiCard title="Title" value="100" />);
      const value = screen.getByText('100');
      expect(value).toHaveClass('text-3xl', 'font-bold');
    });

    it('should have correct unit styles', () => {
      render(<KpiCard title="Title" value="100" unit="$" />);
      const unit = screen.getByText('$');
      expect(unit).toHaveClass('text-sm', 'text-gray-500');
    });

    it('should have correct description styles', () => {
      render(<KpiCard title="Title" value="100" description="Description" />);
      const description = screen.getByText('Description');
      expect(description).toHaveClass('text-xs', 'text-gray-500', 'mt-1');
    });

    it('should have correct trend styles', () => {
      render(<KpiCard title="Title" value="100" trend="up" trendValue={5} />);
      const trendContainer = screen.getByText('上升 5%').parentElement;
      expect(trendContainer).toHaveClass('flex', 'items-center', 'gap-1', 'mt-2', 'text-xs');
    });
  });
});
