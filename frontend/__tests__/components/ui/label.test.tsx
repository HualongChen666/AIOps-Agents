import React from 'react';
import { render, screen } from '@testing-library/react';
import { Label } from '@/components/ui/label';

describe('Label Component', () => {
  describe('Rendering', () => {
    it('should render label with children', () => {
      render(<Label>Test Label</Label>);
      expect(screen.getByText('Test Label')).toBeInTheDocument();
    });

    it('should render label with htmlFor attribute', () => {
      render(<Label htmlFor="test-input">Test Label</Label>);
      const label = screen.getByText('Test Label');
      expect(label).toHaveAttribute('for', 'test-input');
    });

    it('should render required indicator when required prop is true', () => {
      render(<Label required>Test Label</Label>);
      const label = screen.getByText('Test Label');
      expect(label).toBeInTheDocument();
      expect(screen.getByText('*')).toBeInTheDocument();
    });

    it('should not render required indicator when required prop is false', () => {
      render(<Label required={false}>Test Label</Label>);
      const label = screen.getByText('Test Label');
      expect(label).toBeInTheDocument();
      expect(screen.queryByText('*')).not.toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(<Label className="custom-class">Test Label</Label>);
      const label = screen.getByText('Test Label');
      expect(label).toHaveClass('custom-class');
    });

    it('should forward ref correctly', () => {
      const ref = React.createRef<HTMLLabelElement>();
      render(<Label ref={ref}>Test Label</Label>);
      expect(ref.current).toBeInstanceOf(HTMLLabelElement);
    });

    it('should spread additional props to label element', () => {
      render(<Label data-testid="test-label">Test Label</Label>);
      expect(screen.getByTestId('test-label')).toBeInTheDocument();
    });

    it('should handle disabled state with peer-disabled styles', () => {
      render(
        <div className="peer-disabled:cursor-not-allowed">
          <Label>Test Label</Label>
        </div>
      );
      const label = screen.getByText('Test Label');
      expect(label).toBeInTheDocument();
    });
  });

  describe('Props Combinations', () => {
    it('should render with all props combined', () => {
      render(
        <Label
          htmlFor="test-input"
          required
          className="custom-class"
          data-testid="full-label"
        >
          Full Test Label
        </Label>
      );
      const label = screen.getByText('Full Test Label');
      expect(label).toHaveAttribute('for', 'test-input');
      expect(screen.getByText('*')).toBeInTheDocument();
      expect(label).toHaveClass('custom-class');
      expect(screen.getByTestId('full-label')).toBeInTheDocument();
    });

    it('should render without required prop by default', () => {
      render(<Label>Default Label</Label>);
      expect(screen.queryByText('*')).not.toBeInTheDocument();
    });

    it('should render without htmlFor by default', () => {
      render(<Label>No htmlFor Label</Label>);
      const label = screen.getByText('No htmlFor Label');
      expect(label).not.toHaveAttribute('for');
    });
  });

  describe('Edge Cases', () => {
    it('should render empty label', () => {
      render(<Label></Label>);
      const label = screen.queryByRole('label');
      // Empty label might not have role, so check by tag name
      const labelElement = document.querySelector('label');
      expect(labelElement).toBeInTheDocument();
    });

    it('should render label with complex children', () => {
      render(
        <Label>
          <span>Complex</span>
          <span>Label</span>
        </Label>
      );
      expect(screen.getByText('Complex')).toBeInTheDocument();
      expect(screen.getByText('Label')).toBeInTheDocument();
    });

    it('should render label with HTML entities', () => {
      render(<Label>Test & Label</Label>);
      expect(screen.getByText('Test & Label')).toBeInTheDocument();
    });

    it('should handle very long text', () => {
      const longText = 'A'.repeat(1000);
      render(<Label>{longText}</Label>);
      expect(screen.getByText(longText)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper label role', () => {
      render(<Label>Accessible Label</Label>);
      const label = screen.getByText('Accessible Label');
      expect(label.tagName).toBe('LABEL');
    });

    it('should associate with input via htmlFor', () => {
      render(
        <>
          <Label htmlFor="accessible-input">Accessible Label</Label>
          <input id="accessible-input" />
        </>
      );
      const label = screen.getByText('Accessible Label');
      const input = screen.getByRole('textbox');
      expect(label).toHaveAttribute('for', 'accessible-input');
      expect(input).toHaveAttribute('id', 'accessible-input');
    });
  });

  describe('Styling', () => {
    it('should have default base classes', () => {
      render(<Label>Styled Label</Label>);
      const label = screen.getByText('Styled Label');
      expect(label).toHaveClass('text-sm');
      expect(label).toHaveClass('font-medium');
      expect(label).toHaveClass('leading-none');
    });

    it('should merge custom classes with base classes', () => {
      render(<Label className="text-red-500">Styled Label</Label>);
      const label = screen.getByText('Styled Label');
      expect(label).toHaveClass('text-sm');
      expect(label).toHaveClass('text-red-500');
    });
  });
});
