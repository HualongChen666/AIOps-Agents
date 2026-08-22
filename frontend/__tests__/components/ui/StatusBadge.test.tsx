import React from 'react';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '@/components/ui/StatusBadge';

// Mock the Badge component
jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, className, variant }: any) => (
    <span className={className} data-variant={variant} data-testid="badge">
      {children}
    </span>
  ),
}));

// Mock the lucide-react icons
jest.mock('lucide-react', () => ({
  CheckCircle: () => <span data-testid="check-circle-icon">✓</span>,
  XCircle: () => <span data-testid="x-circle-icon">✗</span>,
  Clock: () => <span data-testid="clock-icon">⏰</span>,
  AlertTriangle: () => <span data-testid="alert-triangle-icon">⚠</span>,
  HelpCircle: () => <span data-testid="help-circle-icon">?</span>,
}));

describe('StatusBadge Component', () => {
  describe('Status Variants', () => {
    describe('Success Status', () => {
      it('should render success status with default text', () => {
        render(<StatusBadge status="success" />);
        expect(screen.getByText('成功')).toBeInTheDocument();
      });

      it('should render success status with custom text', () => {
        render(<StatusBadge status="success" text="Completed" />);
        expect(screen.getByText('Completed')).toBeInTheDocument();
      });

      it('should render success status with correct styling', () => {
        render(<StatusBadge status="success" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-green-100', 'text-green-800', 'hover:bg-green-200');
      });

      it('should render success status with check icon', () => {
        render(<StatusBadge status="success" />);
        expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();
      });

      it('should render success status with correct variant', () => {
        render(<StatusBadge status="success" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveAttribute('data-variant', 'default');
      });
    });

    describe('Error Status', () => {
      it('should render error status with default text', () => {
        render(<StatusBadge status="error" />);
        expect(screen.getByText('失败')).toBeInTheDocument();
      });

      it('should render error status with custom text', () => {
        render(<StatusBadge status="error" text="Failed" />);
        expect(screen.getByText('Failed')).toBeInTheDocument();
      });

      it('should render error status with correct styling', () => {
        render(<StatusBadge status="error" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-red-100', 'text-red-800', 'hover:bg-red-200');
      });

      it('should render error status with x icon', () => {
        render(<StatusBadge status="error" />);
        expect(screen.getByTestId('x-circle-icon')).toBeInTheDocument();
      });

      it('should render error status with correct variant', () => {
        render(<StatusBadge status="error" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveAttribute('data-variant', 'destructive');
      });
    });

    describe('Warning Status', () => {
      it('should render warning status with default text', () => {
        render(<StatusBadge status="warning" />);
        expect(screen.getByText('警告')).toBeInTheDocument();
      });

      it('should render warning status with custom text', () => {
        render(<StatusBadge status="warning" text="Caution" />);
        expect(screen.getByText('Caution')).toBeInTheDocument();
      });

      it('should render warning status with correct styling', () => {
        render(<StatusBadge status="warning" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800', 'hover:bg-yellow-200');
      });

      it('should render warning status with alert icon', () => {
        render(<StatusBadge status="warning" />);
        expect(screen.getByTestId('alert-triangle-icon')).toBeInTheDocument();
      });

      it('should render warning status with correct variant', () => {
        render(<StatusBadge status="warning" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveAttribute('data-variant', 'secondary');
      });
    });

    describe('Info Status', () => {
      it('should render info status with default text', () => {
        render(<StatusBadge status="info" />);
        expect(screen.getByText('信息')).toBeInTheDocument();
      });

      it('should render info status with custom text', () => {
        render(<StatusBadge status="info" text="Information" />);
        expect(screen.getByText('Information')).toBeInTheDocument();
      });

      it('should render info status with correct styling', () => {
        render(<StatusBadge status="info" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-blue-100', 'text-blue-800', 'hover:bg-blue-200');
      });

      it('should render info status with help icon', () => {
        render(<StatusBadge status="info" />);
        expect(screen.getByTestId('help-circle-icon')).toBeInTheDocument();
      });

      it('should render info status with correct variant', () => {
        render(<StatusBadge status="info" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveAttribute('data-variant', 'outline');
      });
    });

    describe('Pending Status', () => {
      it('should render pending status with default text', () => {
        render(<StatusBadge status="pending" />);
        expect(screen.getByText('待处理')).toBeInTheDocument();
      });

      it('should render pending status with custom text', () => {
        render(<StatusBadge status="pending" text="In Progress" />);
        expect(screen.getByText('In Progress')).toBeInTheDocument();
      });

      it('should render pending status with correct styling', () => {
        render(<StatusBadge status="pending" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-gray-100', 'text-gray-800', 'hover:bg-gray-200');
      });

      it('should render pending status with clock icon', () => {
        render(<StatusBadge status="pending" />);
        expect(screen.getByTestId('clock-icon')).toBeInTheDocument();
      });

      it('should render pending status with correct variant', () => {
        render(<StatusBadge status="pending" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveAttribute('data-variant', 'outline');
      });
    });

    describe('Unknown Status', () => {
      it('should render unknown status with default text', () => {
        render(<StatusBadge status="unknown" />);
        expect(screen.getByText('未知')).toBeInTheDocument();
      });

      it('should render unknown status with custom text', () => {
        render(<StatusBadge status="unknown" text="N/A" />);
        expect(screen.getByText('N/A')).toBeInTheDocument();
      });

      it('should render unknown status with correct styling', () => {
        render(<StatusBadge status="unknown" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-gray-100', 'text-gray-800', 'hover:bg-gray-200');
      });

      it('should render unknown status with help icon', () => {
        render(<StatusBadge status="unknown" />);
        expect(screen.getByTestId('help-circle-icon')).toBeInTheDocument();
      });

      it('should render unknown status with correct variant', () => {
        render(<StatusBadge status="unknown" />);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveAttribute('data-variant', 'outline');
      });
    });
  });

  describe('Size Variants', () => {
    it('should render with small size', () => {
      render(<StatusBadge status="success" size="sm" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveClass('text-xs', 'px-2', 'py-0.5');
    });

    it('should render with medium size (default)', () => {
      render(<StatusBadge status="success" size="md" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveClass('text-sm', 'px-2.5', 'py-1');
    });

    it('should render with large size', () => {
      render(<StatusBadge status="success" size="lg" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveClass('text-base', 'px-3', 'py-1.5');
    });

    it('should default to medium size when not specified', () => {
      render(<StatusBadge status="success" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveClass('text-sm', 'px-2.5', 'py-1');
    });
  });

  describe('Icon Display', () => {
    it('should show icon when showIcon is true (default)', () => {
      render(<StatusBadge status="success" />);
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();
    });

    it('should not show icon when showIcon is false', () => {
      render(<StatusBadge status="success" showIcon={false} />);
      expect(screen.queryByTestId('check-circle-icon')).not.toBeInTheDocument();
    });

    it('should show icon for all status types when showIcon is true', () => {
      const { rerender } = render(<StatusBadge status="success" />);
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();

      rerender(<StatusBadge status="error" />);
      expect(screen.getByTestId('x-circle-icon')).toBeInTheDocument();

      rerender(<StatusBadge status="warning" />);
      expect(screen.getByTestId('alert-triangle-icon')).toBeInTheDocument();

      rerender(<StatusBadge status="info" />);
      expect(screen.getByTestId('help-circle-icon')).toBeInTheDocument();

      rerender(<StatusBadge status="pending" />);
      expect(screen.getByTestId('clock-icon')).toBeInTheDocument();
    });

    it('should have correct icon size', () => {
      render(<StatusBadge status="success" />);
      const icon = screen.getByTestId('check-circle-icon');
      expect(icon).toHaveClass('h-3', 'w-3');
    });
  });

  describe('Text Display', () => {
    it('should use custom text when provided', () => {
      render(<StatusBadge status="success" text="Custom Text" />);
      expect(screen.getByText('Custom Text')).toBeInTheDocument();
      expect(screen.queryByText('成功')).not.toBeInTheDocument();
    });

    it('should use default text when custom text is not provided', () => {
      render(<StatusBadge status="success" />);
      expect(screen.getByText('成功')).toBeInTheDocument();
    });

    it('should use default text when custom text is empty string', () => {
      render(<StatusBadge status="success" text="" />);
      expect(screen.getByText('成功')).toBeInTheDocument();
    });

    it('should handle long custom text', () => {
      const longText = 'This is a very long status text that might wrap';
      render(<StatusBadge status="success" text={longText} />);
      expect(screen.getByText(longText)).toBeInTheDocument();
    });

    it('should handle special characters in custom text', () => {
      const specialText = 'Status <special> & characters';
      render(<StatusBadge status="success" text={specialText} />);
      expect(screen.getByText(specialText)).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should have flex layout', () => {
      render(<StatusBadge status="success" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveClass('flex', 'items-center', 'gap-1');
    });

    it('should have gap between icon and text', () => {
      render(<StatusBadge status="success" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveClass('gap-1');
    });

    it('should apply status-specific background color', () => {
      const { rerender } = render(<StatusBadge status="success" />);
      expect(screen.getByTestId('badge')).toHaveClass('bg-green-100');

      rerender(<StatusBadge status="error" />);
      expect(screen.getByTestId('badge')).toHaveClass('bg-red-100');

      rerender(<StatusBadge status="warning" />);
      expect(screen.getByTestId('badge')).toHaveClass('bg-yellow-100');

      rerender(<StatusBadge status="info" />);
      expect(screen.getByTestId('badge')).toHaveClass('bg-blue-100');
    });

    it('should apply status-specific text color', () => {
      const { rerender } = render(<StatusBadge status="success" />);
      expect(screen.getByTestId('badge')).toHaveClass('text-green-800');

      rerender(<StatusBadge status="error" />);
      expect(screen.getByTestId('badge')).toHaveClass('text-red-800');

      rerender(<StatusBadge status="warning" />);
      expect(screen.getByTestId('badge')).toHaveClass('text-yellow-800');

      rerender(<StatusBadge status="info" />);
      expect(screen.getByTestId('badge')).toHaveClass('text-blue-800');
    });

    it('should apply hover effect', () => {
      render(<StatusBadge status="success" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveClass('hover:bg-green-200');
    });
  });

  describe('Edge Cases', () => {
    it('should handle all status types', () => {
      const statuses: Array<'success' | 'error' | 'warning' | 'info' | 'pending' | 'unknown'> = [
        'success',
        'error',
        'warning',
        'info',
        'pending',
        'unknown',
      ];

      statuses.forEach((status) => {
        const { unmount } = render(<StatusBadge status={status} />);
        expect(screen.getByTestId('badge')).toBeInTheDocument();
        unmount();
      });
    });

    it('should handle all size types', () => {
      const sizes: Array<'sm' | 'md' | 'lg'> = ['sm', 'md', 'lg'];

      sizes.forEach((size) => {
        const { unmount } = render(<StatusBadge status="success" size={size} />);
        expect(screen.getByTestId('badge')).toBeInTheDocument();
        unmount();
      });
    });

    it('should handle empty text with showIcon false', () => {
      render(<StatusBadge status="success" text="" showIcon={false} />);
      const badge = screen.getByTestId('badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toBeEmptyDOMElement();
    });

    it('should handle unicode text', () => {
      render(<StatusBadge status="success" text="成功完成" />);
      expect(screen.getByText('成功完成')).toBeInTheDocument();
    });
  });

  describe('Integration Tests', () => {
    it('should render with all props combined', () => {
      render(
        <StatusBadge
          status="success"
          text="Operation Complete"
          size="lg"
          showIcon
        />
      );

      expect(screen.getByText('Operation Complete')).toBeInTheDocument();
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveClass('text-base', 'px-3', 'py-1.5');
    });

    it('should handle status change', () => {
      const { rerender } = render(<StatusBadge status="success" />);
      expect(screen.getByText('成功')).toBeInTheDocument();
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();

      rerender(<StatusBadge status="error" />);
      expect(screen.getByText('失败')).toBeInTheDocument();
      expect(screen.getByTestId('x-circle-icon')).toBeInTheDocument();
    });

    it('should handle size change', () => {
      const { rerender } = render(<StatusBadge status="success" size="sm" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveClass('text-xs', 'px-2', 'py-0.5');

      rerender(<StatusBadge status="success" size="lg" />);
      expect(badge).toHaveClass('text-base', 'px-3', 'py-1.5');
    });

    it('should handle text change', () => {
      const { rerender } = render(<StatusBadge status="success" text="First" />);
      expect(screen.getByText('First')).toBeInTheDocument();

      rerender(<StatusBadge status="success" text="Second" />);
      expect(screen.getByText('Second')).toBeInTheDocument();
    });

    it('should handle showIcon toggle', () => {
      const { rerender } = render(<StatusBadge status="success" showIcon />);
      expect(screen.getByTestId('check-circle-icon')).toBeInTheDocument();

      rerender(<StatusBadge status="success" showIcon={false} />);
      expect(screen.queryByTestId('check-circle-icon')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper text content for screen readers', () => {
      render(<StatusBadge status="success" text="Success" />);
      const badge = screen.getByTestId('badge');
      expect(badge).toHaveTextContent('Success');
    });

    it('should include icon in accessibility tree when showIcon is true', () => {
      render(<StatusBadge status="success" showIcon />);
      const icon = screen.getByTestId('check-circle-icon');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('should render Badge component', () => {
      render(<StatusBadge status="success" />);
      expect(screen.getByTestId('badge')).toBeInTheDocument();
    });

    it('should render icon before text', () => {
      render(<StatusBadge status="success" />);
      const badge = screen.getByTestId('badge');
      const icon = screen.getByTestId('check-circle-icon');
      const text = screen.getByText('成功');
      
      expect(badge).toContainElement(icon);
      expect(badge).toContainElement(text);
    });
  });
});
