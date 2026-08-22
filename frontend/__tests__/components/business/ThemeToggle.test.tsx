import React from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from '@/components/ThemeProvider';
import { ThemeToggle } from '@/components/ThemeToggle';

describe('ThemeToggle Component', () => {
  beforeEach(() => {
    localStorage.clear();
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
  });

  describe('Rendering', () => {
    it('should render toggle button', () => {
      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should show moon icon in light mode', () => {
      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      expect(screen.getByText('☾')).toBeInTheDocument();
    });

    it('should show sun icon in dark mode', () => {
      localStorage.setItem('aiops-theme', 'dark');

      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      expect(screen.getByText('☀')).toBeInTheDocument();
    });
  });

  describe('Theme Toggle Functionality', () => {
    it('should toggle theme when clicked', async () => {
      const user = userEvent.setup();

      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      expect(screen.getByText('☾')).toBeInTheDocument();

      const button = screen.getByRole('button');
      await user.click(button);

      expect(screen.getByText('☀')).toBeInTheDocument();
    });

    it('should toggle back to light mode', async () => {
      const user = userEvent.setup();
      localStorage.setItem('aiops-theme', 'dark');

      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      expect(screen.getByText('☀')).toBeInTheDocument();

      const button = screen.getByRole('button');
      await user.click(button);

      expect(screen.getByText('☾')).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply correct button styles', () => {
      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass('text-sm');
      expect(button).toHaveClass('px-2');
      expect(button).toHaveClass('py-1');
      expect(button).toHaveClass('border');
    });

    it('should apply hover effects', () => {
      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass('hover:bg-gray-200');
    });

    it('should apply transition effects', () => {
      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      const button = screen.getByRole('button');
      expect(button).toHaveClass('transition');
    });
  });

  describe('Accessibility', () => {
    it('should have aria-label', () => {
      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'toggle theme');
    });

    it('should be keyboard accessible', async () => {
      const user = userEvent.setup();

      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      const button = screen.getByRole('button');
      button.focus();
      expect(button).toHaveFocus();

      await user.keyboard('{Enter}');

      expect(screen.getByText('☀')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle rapid clicks', async () => {
      const user = userEvent.setup();

      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      const button = screen.getByRole('button');

      await user.click(button);
      await user.click(button);
      await user.click(button);

      expect(screen.getByText('☾')).toBeInTheDocument();
    });

    it('should work when used without ThemeProvider (should throw)', () => {
      // This test verifies that the component properly requires ThemeProvider
      expect(() => {
        render(<ThemeToggle />);
      }).toThrow();
    });
  });

  describe('Integration with ThemeProvider', () => {
    it('should sync with ThemeProvider state', async () => {
      const user = userEvent.setup();

      render(
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      );

      const button = screen.getByRole('button');

      await user.click(button);
      expect(localStorage.getItem('aiops-theme')).toBe('dark');

      await user.click(button);
      expect(localStorage.getItem('aiops-theme')).toBe('light');
    });
  });
});
