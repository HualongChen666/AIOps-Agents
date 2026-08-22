import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AlertItem } from '@/components/ui/AlertItem';

// Mock the Badge component
jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, className, variant }: any) => (
    <span className={className} data-variant={variant} data-testid="badge">
      {children}
    </span>
  ),
}));

// Mock the Button component
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, size, variant }: any) => (
    <button onClick={onClick} data-size={size} data-variant={variant}>
      {children}
    </button>
  ),
}));

// Mock the lucide-react icons
jest.mock('lucide-react', () => ({
  AlertTriangle: ({ className }: any) => <span className={className} data-testid="alert-triangle">⚠</span>,
  CheckCircle: ({ className }: any) => <span className={className} data-testid="check-circle">✓</span>,
  XCircle: ({ className }: any) => <span className={className} data-testid="x-circle">✗</span>,
  Clock: ({ className }: any) => <span className={className} data-testid="clock">⏰</span>,
}));

describe('AlertItem Component', () => {
  const defaultProps = {
    id: '1',
    title: 'Test Alert',
    severity: 'high' as const,
    status: 'open' as const,
    timestamp: '2024-01-01T00:00:00Z',
  };

  describe('Rendering', () => {
    it('should render alert with required props', () => {
      render(<AlertItem {...defaultProps} />);
      expect(screen.getByText('Test Alert')).toBeInTheDocument();
    });

    it('should render with service', () => {
      render(<AlertItem {...defaultProps} service="API Service" />);
      expect(screen.getByText('API Service')).toBeInTheDocument();
    });

    it('should render with details', () => {
      render(<AlertItem {...defaultProps} details="Additional details about the alert" />);
      expect(screen.getByText('Additional details about the alert')).toBeInTheDocument();
    });

    it('should render with timestamp', () => {
      render(<AlertItem {...defaultProps} />);
      expect(screen.getByText(/2024/)).toBeInTheDocument();
    });

    it('should render with view button when onView is provided', () => {
      render(<AlertItem {...defaultProps} onView={() => {}} />);
      expect(screen.getByText('查看')).toBeInTheDocument();
    });

    it('should render with acknowledge button when onAcknowledge is provided and status is open', () => {
      render(<AlertItem {...defaultProps} onAcknowledge={() => {}} />);
      expect(screen.getByText('确认')).toBeInTheDocument();
    });

    it('should render with resolve button when onResolve is provided and status is not resolved', () => {
      render(<AlertItem {...defaultProps} onResolve={() => {}} />);
      expect(screen.getByText('解决')).toBeInTheDocument();
    });
  });

  describe('Severity Variants', () => {
    it('should render critical severity', () => {
      render(<AlertItem {...defaultProps} severity="critical" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveTextContent('严重');
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should render high severity', () => {
      render(<AlertItem {...defaultProps} severity="high" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveTextContent('高');
      expect(badge).toHaveClass('bg-orange-100', 'text-orange-800');
    });

    it('should render medium severity', () => {
      render(<AlertItem {...defaultProps} severity="medium" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveTextContent('中');
      expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
    });

    it('should render low severity', () => {
      render(<AlertItem {...defaultProps} severity="low" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveTextContent('低');
      expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });
  });

  describe('Status Variants', () => {
    it('should render open status with alert icon', () => {
      render(<AlertItem {...defaultProps} status="open" />);
      expect(screen.getByTestId('alert-triangle')).toBeInTheDocument();
      expect(screen.getByText('未处理')).toBeInTheDocument();
    });

    it('should render acknowledged status with clock icon', () => {
      render(<AlertItem {...defaultProps} status="acknowledged" />);
      expect(screen.getByTestId('clock')).toBeInTheDocument();
      expect(screen.getByText('已确认')).toBeInTheDocument();
    });

    it('should render resolved status with check icon', () => {
      render(<AlertItem {...defaultProps} status="resolved" />);
      expect(screen.getByTestId('check-circle')).toBeInTheDocument();
      expect(screen.getByText('已解决')).toBeInTheDocument();
    });

    it('should not show acknowledge button when status is not open', () => {
      render(<AlertItem {...defaultProps} status="acknowledged" onAcknowledge={() => {}} />);
      expect(screen.queryByText('确认')).not.toBeInTheDocument();
    });

    it('should not show resolve button when status is resolved', () => {
      render(<AlertItem {...defaultProps} status="resolved" onResolve={() => {}} />);
      expect(screen.queryByText('解决')).not.toBeInTheDocument();
    });
  });

  describe('Event Handling', () => {
    it('should call onView with id when view button is clicked', async () => {
      const handleView = jest.fn();
      const user = userEvent.setup();
      render(<AlertItem {...defaultProps} onView={handleView} />);
      
      await user.click(screen.getByText('查看'));
      expect(handleView).toHaveBeenCalledWith('1');
    });

    it('should call onAcknowledge with id when acknowledge button is clicked', async () => {
      const handleAcknowledge = jest.fn();
      const user = userEvent.setup();
      render(<AlertItem {...defaultProps} onAcknowledge={handleAcknowledge} />);
      
      await user.click(screen.getByText('确认'));
      expect(handleAcknowledge).toHaveBeenCalledWith('1');
    });

    it('should call onResolve with id when resolve button is clicked', async () => {
      const handleResolve = jest.fn();
      const user = userEvent.setup();
      render(<AlertItem {...defaultProps} onResolve={handleResolve} />);
      
      await user.click(screen.getByText('解决'));
      expect(handleResolve).toHaveBeenCalledWith('1');
    });
  });

  describe('Button Visibility', () => {
    it('should show all buttons when all handlers are provided and status is open', () => {
      render(
        <AlertItem
          {...defaultProps}
          onView={() => {}}
          onAcknowledge={() => {}}
          onResolve={() => {}}
        />
      );
      expect(screen.getByText('查看')).toBeInTheDocument();
      expect(screen.getByText('确认')).toBeInTheDocument();
      expect(screen.getByText('解决')).toBeInTheDocument();
    });

    it('should not show acknowledge button when onAcknowledge is not provided', () => {
      render(<AlertItem {...defaultProps} status="open" />);
      expect(screen.queryByText('确认')).not.toBeInTheDocument();
    });

    it('should not show view button when onView is not provided', () => {
      render(<AlertItem {...defaultProps} />);
      expect(screen.queryByText('查看')).not.toBeInTheDocument();
    });

    it('should not show resolve button when onResolve is not provided', () => {
      render(<AlertItem {...defaultProps} />);
      expect(screen.queryByText('解决')).not.toBeInTheDocument();
    });
  });

  describe('Timestamp Display', () => {
    it('should format timestamp correctly', () => {
      render(<AlertItem {...defaultProps} timestamp="2024-01-15T10:30:00Z" />);
      expect(screen.getByText(/2024/)).toBeInTheDocument();
    });

    it('should handle different timestamp formats', () => {
      render(<AlertItem {...defaultProps} timestamp="2024-12-31T23:59:59Z" />);
      expect(screen.getByText(/2024/)).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty title', () => {
      render(<AlertItem {...defaultProps} title="" />);
      const title = screen.getByRole('heading');
      expect(title).toBeInTheDocument();
    });

    it('should handle long title', () => {
      const longTitle = 'This is a very long alert title that might need to be truncated';
      render(<AlertItem {...defaultProps} title={longTitle} />);
      expect(screen.getByText(longTitle)).toBeInTheDocument();
    });

    it('should handle long details', () => {
      const longDetails = 'This is a very long details text that might need to be truncated with line-clamp-2 class applied';
      render(<AlertItem {...defaultProps} details={longDetails} />);
      expect(screen.getByText(longDetails)).toBeInTheDocument();
    });

    it('should handle special characters in title', () => {
      render(<AlertItem {...defaultProps} title="Alert <special> & characters" />);
      expect(screen.getByText(/Alert/)).toBeInTheDocument();
    });

    it('should handle unicode characters', () => {
      render(<AlertItem {...defaultProps} title="警报消息 🚨" />);
      expect(screen.getByText(/警报/)).toBeInTheDocument();
    });

    it('should handle missing service', () => {
      render(<AlertItem {...defaultProps} />);
      expect(screen.queryByText(/service/i)).not.toBeInTheDocument();
    });

    it('should handle missing details', () => {
      render(<AlertItem {...defaultProps} />);
      const details = screen.queryByText(/details/i);
      expect(details).not.toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should have correct base styles', () => {
      render(<AlertItem {...defaultProps} />);
      const container = screen.getByText('Test Alert').parentElement?.parentElement;
      expect(container).toHaveClass('flex', 'items-start', 'gap-4', 'p-4', 'border', 'rounded-lg', 'hover:bg-gray-50', 'transition');
    });

    it('should have correct title styling', () => {
      render(<AlertItem {...defaultProps} />);
      const title = screen.getByRole('heading');
      expect(title).toHaveClass('font-medium', 'text-gray-900', 'truncate');
    });

    it('should have correct service styling', () => {
      render(<AlertItem {...defaultProps} service="API" />);
      const service = screen.getByText('API');
      expect(service).toHaveClass('text-sm', 'text-gray-500');
    });

    it('should have correct details styling', () => {
      render(<AlertItem {...defaultProps} details="Details" />);
      const details = screen.getByText('Details');
      expect(details).toHaveClass('text-sm', 'text-gray-600', 'mt-1', 'line-clamp-2');
    });

    it('should have correct timestamp styling', () => {
      render(<AlertItem {...defaultProps} />);
      const timestamp = screen.getByText(/2024/);
      expect(timestamp).toHaveClass('text-xs', 'text-gray-500');
    });
  });

  describe('Status Icon Styling', () => {
    it('should have correct icon color for open status', () => {
      render(<AlertItem {...defaultProps} status="open" />);
      const icon = screen.getByTestId('alert-triangle');
      expect(icon).toHaveClass('text-red-500');
    });

    it('should have correct icon color for acknowledged status', () => {
      render(<AlertItem {...defaultProps} status="acknowledged" />);
      const icon = screen.getByTestId('clock');
      expect(icon).toHaveClass('text-yellow-500');
    });

    it('should have correct icon color for resolved status', () => {
      render(<AlertItem {...defaultProps} status="resolved" />);
      const icon = screen.getByTestId('check-circle');
      expect(icon).toHaveClass('text-green-500');
    });

    it('should have correct icon size', () => {
      render(<AlertItem {...defaultProps} />);
      const icon = screen.getByTestId('alert-triangle');
      expect(icon).toHaveClass('h-4', 'w-4');
    });
  });

  describe('Integration Tests', () => {
    it('should handle complete alert with all props', () => {
      render(
        <AlertItem
          id="1"
          title="Server Down"
          severity="critical"
          status="open"
          timestamp="2024-01-01T00:00:00Z"
          service="Web Server"
          details="Server is not responding to requests"
          onView={() => {}}
          onAcknowledge={() => {}}
          onResolve={() => {}}
        />
      );

      expect(screen.getByText('Server Down')).toBeInTheDocument();
      expect(screen.getByText('Web Server')).toBeInTheDocument();
      expect(screen.getByText('Server is not responding to requests')).toBeInTheDocument();
      expect(screen.getByText('严重')).toBeInTheDocument();
      expect(screen.getByText('未处理')).toBeInTheDocument();
      expect(screen.getByText('查看')).toBeInTheDocument();
      expect(screen.getByText('确认')).toBeInTheDocument();
      expect(screen.getByText('解决')).toBeInTheDocument();
    });

    it('should handle status change', () => {
      const { rerender } = render(<AlertItem {...defaultProps} status="open" />);
      expect(screen.getByTestId('alert-triangle')).toBeInTheDocument();
      expect(screen.getByText('未处理')).toBeInTheDocument();

      rerender(<AlertItem {...defaultProps} status="resolved" />);
      expect(screen.getByTestId('check-circle')).toBeInTheDocument();
      expect(screen.getByText('已解决')).toBeInTheDocument();
    });

    it('should handle severity change', () => {
      const { rerender } = render(<AlertItem {...defaultProps} severity="high" />);
      expect(screen.getByText('高')).toBeInTheDocument();

      rerender(<AlertItem {...defaultProps} severity="critical" />);
      expect(screen.getByText('严重')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading structure', () => {
      render(<AlertItem {...defaultProps} />);
      const title = screen.getByRole('heading');
      expect(title).toBeInTheDocument();
    });

    it('should have accessible buttons', () => {
      render(
        <AlertItem
          {...defaultProps}
          onView={() => {}}
          onAcknowledge={() => {}}
          onResolve={() => {}}
        />
      );
      expect(screen.getByRole('button', { name: '查看' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '确认' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '解决' })).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('should have correct element hierarchy', () => {
      render(<AlertItem {...defaultProps} />);
      const container = screen.getByText('Test Alert').parentElement?.parentElement;
      expect(container).toBeInTheDocument();
    });

    it('should render status icon in correct position', () => {
      render(<AlertItem {...defaultProps} />);
      const icon = screen.getByTestId('alert-triangle');
      const iconContainer = icon.parentElement;
      expect(iconContainer).toHaveClass('flex-shrink-0', 'mt-1');
    });

    it('should render buttons in correct order', () => {
      render(
        <AlertItem
          {...defaultProps}
          onView={() => {}}
          onAcknowledge={() => {}}
          onResolve={() => {}}
        />
      );
      const buttons = screen.getAllByRole('button');
      expect(buttons[0]).toHaveTextContent('查看');
      expect(buttons[1]).toHaveTextContent('确认');
      expect(buttons[2]).toHaveTextContent('解决');
    });
  });

  describe('Conditional Rendering', () => {
    it('should not render service when not provided', () => {
      render(<AlertItem {...defaultProps} />);
      expect(screen.queryByText(/service/i)).not.toBeInTheDocument();
    });

    it('should not render details when not provided', () => {
      render(<AlertItem {...defaultProps} />);
      expect(screen.queryByText(/details/i)).not.toBeInTheDocument();
    });

    it('should not render view button when onView is not provided', () => {
      render(<AlertItem {...defaultProps} />);
      expect(screen.queryByText('查看')).not.toBeInTheDocument();
    });

    it('should not render acknowledge button when onAcknowledge is not provided', () => {
      render(<AlertItem {...defaultProps} />);
      expect(screen.queryByText('确认')).not.toBeInTheDocument();
    });

    it('should not render resolve button when onResolve is not provided', () => {
      render(<AlertItem {...defaultProps} />);
      expect(screen.queryByText('解决')).not.toBeInTheDocument();
    });
  });
});
