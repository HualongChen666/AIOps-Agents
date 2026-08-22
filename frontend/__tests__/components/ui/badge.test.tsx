import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Badge } from '@/components/ui/badge';

describe('Badge Component', () => {
  describe('Rendering', () => {
    it('should render badge with default props', () => {
      render(<Badge>Badge</Badge>);
      const badge = screen.getByText('Badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('inline-flex', 'items-center', 'rounded-full', 'px-2.5', 'py-0.5', 'text-xs', 'font-medium');
    });

    it('should render badge with custom className', () => {
      render(<Badge className="custom-class">Badge</Badge>);
      const badge = screen.getByText('Badge');
      expect(badge).toHaveClass('custom-class');
    });

    it('should render badge with complex children', () => {
      render(
        <Badge>
          <span>Icon</span>
          <span>Text</span>
        </Badge>
      );
      const badge = screen.getByText('Text');
      expect(badge).toBeInTheDocument();
      expect(screen.getByText('Icon')).toBeInTheDocument();
    });
  });

  describe('Variants', () => {
    it('should render default variant', () => {
      render(<Badge variant="default">Default</Badge>);
      const badge = screen.getByText('Default');
      expect(badge).toHaveClass('bg-blue-100', 'text-blue-800');
    });

    it('should render destructive variant', () => {
      render(<Badge variant="destructive">Destructive</Badge>);
      const badge = screen.getByText('Destructive');
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should render outline variant', () => {
      render(<Badge variant="outline">Outline</Badge>);
      const badge = screen.getByText('Outline');
      expect(badge).toHaveClass('border', 'border-gray-300', 'text-gray-800');
    });

    it('should render secondary variant', () => {
      render(<Badge variant="secondary">Secondary</Badge>);
      const badge = screen.getByText('Secondary');
      expect(badge).toHaveClass('bg-gray-200', 'text-gray-800');
    });
  });

  describe('Event Handling', () => {
    it('should call onClick handler when clicked', async () => {
      const handleClick = jest.fn();
      const user = userEvent.setup();
      render(<Badge onClick={handleClick}>Clickable</Badge>);
      
      const badge = screen.getByText('Clickable');
      await user.click(badge);
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should handle multiple clicks', async () => {
      const handleClick = jest.fn();
      const user = userEvent.setup();
      render(<Badge onClick={handleClick}>Clickable</Badge>);
      
      const badge = screen.getByText('Clickable');
      await user.click(badge);
      await user.click(badge);
      
      expect(handleClick).toHaveBeenCalledTimes(2);
    });
  });

  describe('Props forwarding', () => {
    it('should pass additional HTML attributes', () => {
      render(<Badge data-testid="test-badge" aria-label="Test Badge">Badge</Badge>);
      const badge = screen.getByTestId('test-badge');
      expect(badge).toHaveAttribute('aria-label', 'Test Badge');
    });

    it('should handle id attribute', () => {
      render(<Badge id="badge-id">Badge</Badge>);
      const badge = screen.getByText('Badge');
      expect(badge).toHaveAttribute('id', 'badge-id');
    });

    it('should handle title attribute', () => {
      render(<Badge title="Badge tooltip">Badge</Badge>);
      const badge = screen.getByText('Badge');
      expect(badge).toHaveAttribute('title', 'Badge tooltip');
    });
  });

  describe('Edge Cases', () => {
    it('should render with empty children', () => {
      render(<Badge></Badge>);
      const badge = document.querySelector('.rounded-full');
      expect(badge).toBeInTheDocument();
    });

    it('should render with null children', () => {
      render(<Badge>{null}</Badge>);
      const badge = document.querySelector('.rounded-full');
      expect(badge).toBeInTheDocument();
    });

    it('should render with long text', () => {
      const longText = 'This is a very long badge text that might wrap';
      render(<Badge>{longText}</Badge>);
      const badge = screen.getByText(longText);
      expect(badge).toBeInTheDocument();
    });

    it('should render with special characters', () => {
      const specialChars = 'Badge!@#$%';
      render(<Badge>{specialChars}</Badge>);
      const badge = screen.getByText(specialChars);
      expect(badge).toBeInTheDocument();
    });

    it('should render with numbers', () => {
      render(<Badge>123</Badge>);
      const badge = screen.getByText('123');
      expect(badge).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should support aria-label', () => {
      render(<Badge aria-label="Status badge">Badge</Badge>);
      const badge = screen.getByLabelText('Status badge');
      expect(badge).toBeInTheDocument();
    });

    it('should support role attribute', () => {
      render(<Badge role="status">Badge</Badge>);
      const badge = screen.getByRole('status');
      expect(badge).toBeInTheDocument();
    });

    it('should support aria-live for dynamic badges', () => {
      render(<Badge aria-live="polite">Badge</Badge>);
      const badge = screen.getByText('Badge');
      expect(badge).toHaveAttribute('aria-live', 'polite');
    });
  });

  describe('Styling', () => {
    it('should have correct base styles', () => {
      render(<Badge>Badge</Badge>);
      const badge = screen.getByText('Badge');
      expect(badge).toHaveClass('inline-flex', 'items-center', 'rounded-full');
    });

    it('should have correct text styles', () => {
      render(<Badge>Badge</Badge>);
      const badge = screen.getByText('Badge');
      expect(badge).toHaveClass('text-xs', 'font-medium');
    });

    it('should have correct padding', () => {
      render(<Badge>Badge</Badge>);
      const badge = screen.getByText('Badge');
      expect(badge).toHaveClass('px-2.5', 'py-0.5');
    });
  });
});
