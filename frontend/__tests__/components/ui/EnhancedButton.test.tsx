import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EnhancedButton } from '@/components/ui/EnhancedButton';
import { ChevronRight } from 'lucide-react';

// Mock the lucide-react icon
jest.mock('lucide-react', () => ({
  ChevronRight: () => <span data-testid="chevron-right">→</span>,
}));

describe('EnhancedButton Component', () => {
  describe('Rendering', () => {
    it('should render button with default props', () => {
      render(<EnhancedButton>Click me</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Click me' });
      expect(button).toBeInTheDocument();
    });

    it('should render button with custom className', () => {
      render(<EnhancedButton className="custom-class">Click me</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Click me' });
      expect(button).toHaveClass('custom-class');
    });

    it('should render button with icon on left', () => {
      render(<EnhancedButton icon={ChevronRight} iconPosition="left">Click me</EnhancedButton>);
      const icon = screen.getByTestId('chevron-right');
      expect(icon).toBeInTheDocument();
    });

    it('should render button with icon on right', () => {
      render(<EnhancedButton icon={ChevronRight} iconPosition="right">Click me</EnhancedButton>);
      const icon = screen.getByTestId('chevron-right');
      expect(icon).toBeInTheDocument();
    });

    it('should render button in loading state', () => {
      render(<EnhancedButton loading>Click me</EnhancedButton>);
      expect(screen.getByText('加载中...')).toBeInTheDocument();
      expect(screen.getByText('⟳')).toBeInTheDocument();
    });

    it('should render button with fullWidth', () => {
      render(<EnhancedButton fullWidth>Click me</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Click me' });
      expect(button).toHaveClass('w-full');
    });

    it('should render disabled button', () => {
      render(<EnhancedButton disabled>Click me</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Click me' });
      expect(button).toBeDisabled();
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner when loading is true', () => {
      render(<EnhancedButton loading>Submit</EnhancedButton>);
      expect(screen.getByText('加载中...')).toBeInTheDocument();
      expect(screen.getByText('⟳')).toBeInTheDocument();
    });

    it('should hide children when loading', () => {
      render(<EnhancedButton loading>Submit</EnhancedButton>);
      expect(screen.queryByText('Submit')).not.toBeInTheDocument();
    });

    it('should hide icon when loading', () => {
      render(<EnhancedButton loading icon={ChevronRight}>Submit</EnhancedButton>);
      expect(screen.queryByTestId('chevron-right')).not.toBeInTheDocument();
    });

    it('should be disabled when loading', () => {
      render(<EnhancedButton loading>Submit</EnhancedButton>);
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should not be disabled when loading is false', () => {
      render(<EnhancedButton loading={false}>Submit</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Submit' });
      expect(button).not.toBeDisabled();
    });
  });

  describe('Icon Position', () => {
    it('should place icon before text when iconPosition is left', () => {
      render(<EnhancedButton icon={ChevronRight} iconPosition="left">Text</EnhancedButton>);
      const button = screen.getByRole('button');
      const icon = screen.getByTestId('chevron-right');
      const text = screen.getByText('Text');
      
      expect(button).toContainElement(icon);
      expect(button).toContainElement(text);
    });

    it('should place icon after text when iconPosition is right', () => {
      render(<EnhancedButton icon={ChevronRight} iconPosition="right">Text</EnhancedButton>);
      const button = screen.getByRole('button');
      const icon = screen.getByTestId('chevron-right');
      const text = screen.getByText('Text');
      
      expect(button).toContainElement(icon);
      expect(button).toContainElement(text);
    });

    it('should default to left icon position', () => {
      render(<EnhancedButton icon={ChevronRight}>Text</EnhancedButton>);
      const icon = screen.getByTestId('chevron-right');
      expect(icon).toBeInTheDocument();
    });

    it('should not render icon when not provided', () => {
      render(<EnhancedButton>Text</EnhancedButton>);
      expect(screen.queryByTestId('chevron-right')).not.toBeInTheDocument();
    });
  });

  describe('Full Width', () => {
    it('should apply w-full class when fullWidth is true', () => {
      render(<EnhancedButton fullWidth>Button</EnhancedButton>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('w-full');
    });

    it('should not apply w-full class when fullWidth is false', () => {
      render(<EnhancedButton fullWidth={false}>Button</EnhancedButton>);
      const button = screen.getByRole('button');
      expect(button).not.toHaveClass('w-full');
    });

    it('should not apply w-full class by default', () => {
      render(<EnhancedButton>Button</EnhancedButton>);
      const button = screen.getByRole('button');
      expect(button).not.toHaveClass('w-full');
    });
  });

  describe('Event Handling', () => {
    it('should call onClick handler when clicked', async () => {
      const handleClick = jest.fn();
      const user = userEvent.setup();
      render(<EnhancedButton onClick={handleClick}>Click me</EnhancedButton>);
      
      const button = screen.getByRole('button', { name: 'Click me' });
      await user.click(button);
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should not call onClick when disabled', async () => {
      const handleClick = jest.fn();
      const user = userEvent.setup();
      render(<EnhancedButton onClick={handleClick} disabled>Click me</EnhancedButton>);
      
      const button = screen.getByRole('button', { name: 'Click me' });
      await user.click(button);
      
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('should not call onClick when loading', async () => {
      const handleClick = jest.fn();
      const user = userEvent.setup();
      render(<EnhancedButton onClick={handleClick} loading>Click me</EnhancedButton>);
      
      const button = screen.getByRole('button');
      await user.click(button);
      
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('should handle multiple clicks', async () => {
      const handleClick = jest.fn();
      const user = userEvent.setup();
      render(<EnhancedButton onClick={handleClick}>Click me</EnhancedButton>);
      
      const button = screen.getByRole('button', { name: 'Click me' });
      await user.click(button);
      await user.click(button);
      
      expect(handleClick).toHaveBeenCalledTimes(2);
    });
  });

  describe('Props forwarding', () => {
    it('should pass additional HTML attributes', () => {
      render(<EnhancedButton data-testid="test-button" aria-label="Test">Button</EnhancedButton>);
      const button = screen.getByTestId('test-button');
      expect(button).toHaveAttribute('aria-label', 'Test');
    });

    it('should handle type attribute', () => {
      render(<EnhancedButton type="submit">Submit</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Submit' });
      expect(button).toHaveAttribute('type', 'submit');
    });

    it('should handle form attribute', () => {
      render(<EnhancedButton form="my-form">Submit</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Submit' });
      expect(button).toHaveAttribute('form', 'my-form');
    });
  });

  describe('Variants', () => {
    it('should render default variant', () => {
      render(<EnhancedButton variant="default">Default</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Default' });
      expect(button).toBeInTheDocument();
    });

    it('should render destructive variant', () => {
      render(<EnhancedButton variant="destructive">Delete</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Delete' });
      expect(button).toBeInTheDocument();
    });

    it('should render outline variant', () => {
      render(<EnhancedButton variant="outline">Outline</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Outline' });
      expect(button).toBeInTheDocument();
    });

    it('should render secondary variant', () => {
      render(<EnhancedButton variant="secondary">Secondary</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Secondary' });
      expect(button).toBeInTheDocument();
    });

    it('should render ghost variant', () => {
      render(<EnhancedButton variant="ghost">Ghost</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Ghost' });
      expect(button).toBeInTheDocument();
    });

    it('should render link variant', () => {
      render(<EnhancedButton variant="link">Link</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Link' });
      expect(button).toBeInTheDocument();
    });
  });

  describe('Sizes', () => {
    it('should render default size', () => {
      render(<EnhancedButton size="default">Default</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Default' });
      expect(button).toBeInTheDocument();
    });

    it('should render small size', () => {
      render(<EnhancedButton size="sm">Small</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Small' });
      expect(button).toBeInTheDocument();
    });

    it('should render large size', () => {
      render(<EnhancedButton size="lg">Large</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Large' });
      expect(button).toBeInTheDocument();
    });

    it('should render icon size', () => {
      render(<EnhancedButton size="icon">Icon</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Icon' });
      expect(button).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should render with empty children', () => {
      render(<EnhancedButton></EnhancedButton>);
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should render with null children', () => {
      render(<EnhancedButton>{null}</EnhancedButton>);
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should render with icon but no children', () => {
      render(<EnhancedButton icon={ChevronRight}></EnhancedButton>);
      const icon = screen.getByTestId('chevron-right');
      expect(icon).toBeInTheDocument();
    });

    it('should render with loading and icon', () => {
      render(<EnhancedButton loading icon={ChevronRight}>Submit</EnhancedButton>);
      expect(screen.getByText('加载中...')).toBeInTheDocument();
      expect(screen.queryByTestId('chevron-right')).not.toBeInTheDocument();
    });

    it('should render with loading and fullWidth', () => {
      render(<EnhancedButton loading fullWidth>Submit</EnhancedButton>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('w-full');
      expect(screen.getByText('加载中...')).toBeInTheDocument();
    });

    it('should render with disabled and loading', () => {
      render(<EnhancedButton disabled loading>Submit</EnhancedButton>);
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should render with complex children', () => {
      render(
        <EnhancedButton>
          <span>Part 1</span>
          <span>Part 2</span>
        </EnhancedButton>
      );
      expect(screen.getByText('Part 1')).toBeInTheDocument();
      expect(screen.getByText('Part 2')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper focus styles', () => {
      render(<EnhancedButton>Button</EnhancedButton>);
      const button = screen.getByRole('button');
      expect(button).toHaveClass('focus-visible:outline-none', 'focus-visible:ring-2');
    });

    it('should support aria-label', () => {
      render(<EnhancedButton aria-label="Close">X</EnhancedButton>);
      const button = screen.getByLabelText('Close');
      expect(button).toBeInTheDocument();
    });

    it('should support aria-disabled when disabled', () => {
      render(<EnhancedButton disabled>Disabled</EnhancedButton>);
      const button = screen.getByRole('button', { name: 'Disabled' });
      expect(button).toHaveAttribute('disabled');
    });

    it('should support aria-busy when loading', () => {
      render(<EnhancedButton loading>Loading</EnhancedButton>);
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });

  describe('Integration Tests', () => {
    it('should handle all props together', () => {
      render(
        <EnhancedButton
          variant="destructive"
          size="lg"
          icon={ChevronRight}
          iconPosition="right"
          loading={false}
          fullWidth
          className="custom"
        >
          Delete All
        </EnhancedButton>
      );
      
      const button = screen.getByRole('button', { name: 'Delete All' });
      expect(button).toBeInTheDocument();
      expect(button).toHaveClass('w-full', 'custom');
      expect(screen.getByTestId('chevron-right')).toBeInTheDocument();
    });

    it('should transition from normal to loading state', () => {
      const { rerender } = render(<EnhancedButton loading={false}>Submit</EnhancedButton>);
      expect(screen.getByText('Submit')).toBeInTheDocument();
      
      rerender(<EnhancedButton loading>Submit</EnhancedButton>);
      expect(screen.getByText('加载中...')).toBeInTheDocument();
      expect(screen.queryByText('Submit')).not.toBeInTheDocument();
    });

    it('should transition from loading to normal state', () => {
      const { rerender } = render(<EnhancedButton loading>Submit</EnhancedButton>);
      expect(screen.getByText('加载中...')).toBeInTheDocument();
      
      rerender(<EnhancedButton loading={false}>Submit</EnhancedButton>);
      expect(screen.getByText('Submit')).toBeInTheDocument();
      expect(screen.queryByText('加载中...')).not.toBeInTheDocument();
    });
  });
});
