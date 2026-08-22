import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { ThemeProvider, useTheme } from '@/components/ThemeProvider';

describe('ThemeProvider Component', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Mock matchMedia
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
    it('should render children', () => {
      render(
        <ThemeProvider>
          <div>Test Child</div>
        </ThemeProvider>
      );
      expect(screen.getByText('Test Child')).toBeInTheDocument();
    });

    it('should provide theme context', () => {
      const TestComponent = () => {
        const { theme } = useTheme();
        return <div>Current theme: {theme}</div>;
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText(/Current theme:/)).toBeInTheDocument();
    });
  });

  describe('Theme Initialization', () => {
    it('should initialize with light theme by default', () => {
      const TestComponent = () => {
        const { theme } = useTheme();
        return <div>Theme: {theme}</div>;
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: light')).toBeInTheDocument();
    });

    it('should read theme from localStorage if available', () => {
      localStorage.setItem('aiops-theme', 'dark');
      
      const TestComponent = () => {
        const { theme } = useTheme();
        return <div>Theme: {theme}</div>;
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();
    });

    it('should use system preference if no localStorage value', () => {
      (window.matchMedia as jest.Mock).mockReturnValue({
        matches: true,
        media: '(prefers-color-scheme: dark)',
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      });

      const TestComponent = () => {
        const { theme } = useTheme();
        return <div>Theme: {theme}</div>;
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();
    });
  });

  describe('Theme Toggle', () => {
    it('should toggle theme from light to dark', () => {
      const TestComponent = () => {
        const { theme, toggleTheme } = useTheme();
        return (
          <div>
            <div>Theme: {theme}</div>
            <button onClick={toggleTheme}>Toggle</button>
          </div>
        );
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: light')).toBeInTheDocument();

      act(() => {
        screen.getByText('Toggle').click();
      });

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();
    });

    it('should toggle theme from dark to light', () => {
      localStorage.setItem('aiops-theme', 'dark');
      
      const TestComponent = () => {
        const { theme, toggleTheme } = useTheme();
        return (
          <div>
            <div>Theme: {theme}</div>
            <button onClick={toggleTheme}>Toggle</button>
          </div>
        );
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();

      act(() => {
        screen.getByText('Toggle').click();
      });

      expect(screen.getByText('Theme: light')).toBeInTheDocument();
    });
  });

  describe('DOM Class Management', () => {
    it('should add dark class to html when theme is dark', () => {
      localStorage.setItem('aiops-theme', 'dark');
      
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      );

      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should remove dark class from html when theme is light', () => {
      render(
        <ThemeProvider>
          <div>Test</div>
        </ThemeProvider>
      );

      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });

    it('should update dark class when theme changes', () => {
      const TestComponent = () => {
        const { theme, toggleTheme } = useTheme();
        return (
          <div>
            <div>Theme: {theme}</div>
            <button onClick={toggleTheme}>Toggle</button>
          </div>
        );
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(document.documentElement.classList.contains('dark')).toBe(false);

      act(() => {
        screen.getByText('Toggle').click();
      });

      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });
  });

  describe('LocalStorage Persistence', () => {
    it('should save theme to localStorage on change', () => {
      const TestComponent = () => {
        const { toggleTheme } = useTheme();
        return <button onClick={toggleTheme}>Toggle</button>;
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      act(() => {
        screen.getByText('Toggle').click();
      });

      expect(localStorage.getItem('aiops-theme')).toBe('dark');
    });

    it('should persist theme across re-renders', () => {
      localStorage.setItem('aiops-theme', 'dark');
      
      const TestComponent = () => {
        const { theme } = useTheme();
        return <div>Theme: {theme}</div>;
      };

      const { rerender } = render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();

      rerender(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: dark')).toBeInTheDocument();
    });
  });

  describe('useTheme Hook', () => {
    it('should throw error when used outside ThemeProvider', () => {
      const TestComponent = () => {
        const { theme } = useTheme();
        return <div>Theme: {theme}</div>;
      };

      expect(() => {
        render(<TestComponent />);
      }).toThrow('useTheme must be used within ThemeProvider');
    });

    it('should provide theme and toggleTheme', () => {
      const TestComponent = () => {
        const { theme, toggleTheme } = useTheme();
        return (
          <div>
            <div>Theme: {theme}</div>
            <button onClick={toggleTheme}>Toggle</button>
          </div>
        );
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Theme: light')).toBeInTheDocument();
      expect(screen.getByText('Toggle')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle invalid localStorage value', () => {
      localStorage.setItem('aiops-theme', 'invalid');
      
      const TestComponent = () => {
        const { theme } = useTheme();
        return <div>Theme: {theme}</div>;
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      // Should default to light or system preference
      expect(screen.getByText(/Theme:/)).toBeInTheDocument();
    });

    it('should handle localStorage access errors', () => {
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = jest.fn(() => {
        throw new Error('Storage error');
      });

      const TestComponent = () => {
        const { theme } = useTheme();
        return <div>Theme: {theme}</div>;
      };

      expect(() => {
        render(
          <ThemeProvider>
            <TestComponent />
          </ThemeProvider>
        );
      }).not.toThrow();

      localStorage.getItem = originalGetItem;
    });

    it('should handle rapid theme toggles', () => {
      const TestComponent = () => {
        const { theme, toggleTheme } = useTheme();
        return (
          <div>
            <div>Theme: {theme}</div>
            <button onClick={toggleTheme}>Toggle</button>
          </div>
        );
      };

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );

      const button = screen.getByText('Toggle');

      act(() => {
        button.click();
        button.click();
        button.click();
      });

      expect(screen.getByText('Theme: light')).toBeInTheDocument();
    });
  });

  describe('Integration', () => {
    it('should work with nested components', () => {
      const ChildComponent = () => {
        const { theme } = useTheme();
        return <div>Child theme: {theme}</div>;
      };

      const ParentComponent = () => {
        const { theme, toggleTheme } = useTheme();
        return (
          <div>
            <div>Parent theme: {theme}</div>
            <ChildComponent />
            <button onClick={toggleTheme}>Toggle</button>
          </div>
        );
      };

      render(
        <ThemeProvider>
          <ParentComponent />
        </ThemeProvider>
      );

      expect(screen.getByText('Parent theme: light')).toBeInTheDocument();
      expect(screen.getByText('Child theme: light')).toBeInTheDocument();

      act(() => {
        screen.getByText('Toggle').click();
      });

      expect(screen.getByText('Parent theme: dark')).toBeInTheDocument();
      expect(screen.getByText('Child theme: dark')).toBeInTheDocument();
    });
  });
});
