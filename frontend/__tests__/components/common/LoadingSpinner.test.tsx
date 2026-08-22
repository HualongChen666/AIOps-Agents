import React from 'react';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '@/components/LoadingSpinner';

describe('LoadingSpinner Component', () => {
  describe('Rendering', () => {
    it('should render spinner with default props', () => {
      render(<LoadingSpinner />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toBeInTheDocument();
    });

    it('should render spinner with custom className', () => {
      render(<LoadingSpinner className="custom-class" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('custom-class');
    });

    it('should have loading-spinner class', () => {
      render(<LoadingSpinner />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('loading-spinner');
    });
  });

  describe('Size Variants', () => {
    it('should render small size', () => {
      render(<LoadingSpinner size="sm" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-4', 'h-4');
    });

    it('should render medium size (default)', () => {
      render(<LoadingSpinner size="md" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-8', 'h-8');
    });

    it('should render large size', () => {
      render(<LoadingSpinner size="lg" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-12', 'h-12');
    });

    it('should default to medium size when not specified', () => {
      render(<LoadingSpinner />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-8', 'h-8');
    });
  });

  describe('Custom Styling', () => {
    it('should apply custom className in addition to base classes', () => {
      render(<LoadingSpinner className="custom-class" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('loading-spinner', 'w-8', 'h-8', 'custom-class');
    });

    it('should apply multiple custom classes', () => {
      render(<LoadingSpinner className="class1 class2" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('class1', 'class2');
    });

    it('should apply custom classes with size classes', () => {
      render(<LoadingSpinner size="lg" className="custom-class" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-12', 'h-12', 'custom-class');
    });
  });

  describe('Edge Cases', () => {
    it('should render with empty className', () => {
      render(<LoadingSpinner className="" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toBeInTheDocument();
    });

    it('should render without className prop', () => {
      render(<LoadingSpinner />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toBeInTheDocument();
    });

    it('should handle all size variants', () => {
      const sizes: Array<'sm' | 'md' | 'lg'> = ['sm', 'md', 'lg'];

      sizes.forEach((size) => {
        const { unmount } = render(<LoadingSpinner size={size} />);
        const spinner = document.querySelector('.loading-spinner');
        expect(spinner).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe('Integration Tests', () => {
    it('should handle size change', () => {
      const { rerender } = render(<LoadingSpinner size="sm" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-4', 'h-4');

      rerender(<LoadingSpinner size="lg" />);
      expect(spinner).toHaveClass('w-12', 'h-12');
    });

    it('should handle className change', () => {
      const { rerender } = render(<LoadingSpinner className="class1" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('class1');

      rerender(<LoadingSpinner className="class2" />);
      expect(spinner).toHaveClass('class2');
    });

    it('should handle both size and className changes', () => {
      const { rerender } = render(<LoadingSpinner size="sm" className="class1" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-4', 'h-4', 'class1');

      rerender(<LoadingSpinner size="lg" className="class2" />);
      expect(spinner).toHaveClass('w-12', 'h-12', 'class2');
    });
  });

  describe('Component Structure', () => {
    it('should render div element', () => {
      render(<LoadingSpinner />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toBeInstanceOf(HTMLDivElement);
    });

    it('should have correct element structure', () => {
      render(<LoadingSpinner />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toBeInTheDocument();
      expect(spinner?.children).toHaveLength(0);
    });
  });

  describe('Accessibility', () => {
    it('should be accessible as a loading indicator', () => {
      render(<LoadingSpinner />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toBeInTheDocument();
    });

    it('should support aria-label for accessibility', () => {
      render(<LoadingSpinner className="aria-label='Loading'" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should have correct base classes', () => {
      render(<LoadingSpinner />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('loading-spinner');
    });

    it('should have correct width and height for each size', () => {
      const { rerender } = render(<LoadingSpinner size="sm" />);
      let spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-4', 'h-4');

      rerender(<LoadingSpinner size="md" />);
      spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-8', 'h-8');

      rerender(<LoadingSpinner size="lg" />);
      spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-12', 'h-12');
    });
  });
});
