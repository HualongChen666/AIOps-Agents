import React from 'react';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '@/components/ErrorBoundary';

describe('ErrorBoundary Component', () => {
  describe('Rendering', () => {
    it('should render children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <div>Child Component</div>
        </ErrorBoundary>
      );
      expect(screen.getByText('Child Component')).toBeInTheDocument();
    });

    it('should render custom fallback when error occurs', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary fallback={<div>Custom Fallback</div>}>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('Custom Fallback')).toBeInTheDocument();
    });

    it('should render default error UI when error occurs and no fallback', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('出错了')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should catch errors in child components', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('出错了')).toBeInTheDocument();
    });

    it('should catch errors in nested components', () => {
      const ThrowError = () => {
        throw new Error('Nested error');
      };

      const NestedComponent = () => (
        <div>
          <ThrowError />
        </div>
      );

      render(
        <ErrorBoundary>
          <NestedComponent />
        </ErrorBoundary>
      );
      expect(screen.getByText('出错了')).toBeInTheDocument();
    });

    it('should not catch errors outside boundary', () => {
      const ThrowError = () => {
        throw new Error('Outside error');
      };

      expect(() => {
        render(
          <div>
            <ErrorBoundary>
              <div>Safe Child</div>
            </ErrorBoundary>
            <ThrowError />
          </div>
        );
      }).toThrow('Outside error');
    });
  });

  describe('Default Error UI', () => {
    it('should display error title', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('出错了')).toBeInTheDocument();
    });

    it('should display error message', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('页面加载失败，请刷新重试')).toBeInTheDocument();
    });

    it('should display refresh button', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('刷新页面')).toBeInTheDocument();
    });

    it('should display error details when error is available', () => {
      const ThrowError = () => {
        throw new Error('Test error with details');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('错误详情')).toBeInTheDocument();
    });

    it('should display error message in details', () => {
      const ThrowError = () => {
        throw new Error('Test error message');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      const details = screen.getByText('错误详情').parentElement;
      expect(details).toHaveTextContent('Test error message');
    });
  });

  describe('Custom Fallback', () => {
    it('should render custom fallback component', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      const CustomFallback = () => <div>Custom Error UI</div>;

      render(
        <ErrorBoundary fallback={<CustomFallback />}>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('Custom Error UI')).toBeInTheDocument();
    });

    it('should not render default UI when custom fallback is provided', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary fallback={<div>Custom</div>}>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.queryByText('出错了')).not.toBeInTheDocument();
    });

    it('should render custom fallback with complex content', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      const CustomFallback = () => (
        <div>
          <h1>Custom Error</h1>
          <p>Something went wrong</p>
          <button>Retry</button>
        </div>
      );

      render(
        <ErrorBoundary fallback={<CustomFallback />}>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('Custom Error')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  describe('Refresh Button', () => {
    it('should call window.location.reload when clicked', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const refreshButton = screen.getByText('刷新页面');
      refreshButton.click();

      // window.location.reload is mocked in jest.setup.js
      expect(window.location.reload).toHaveBeenCalled();
    });
  });

  describe('Error Details', () => {
    it('should show error details in details element', () => {
      const ThrowError = () => {
        throw new Error('Detailed error message');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const details = screen.getByText('错误详情').parentElement;
      expect(details?.tagName).toBe('DETAILS');
    });

    it('should have summary element for error details', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const summary = screen.getByText('错误详情');
      expect(summary.tagName).toBe('SUMMARY');
    });

    it('should have pre element for error message', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const pre = document.querySelector('pre');
      expect(pre).toBeInTheDocument();
    });

    it('should display error message in pre element', () => {
      const ThrowError = () => {
        throw new Error('Error: Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const pre = document.querySelector('pre');
      expect(pre).toHaveTextContent('Error: Test error');
    });
  });

  describe('Styling', () => {
    it('should have correct container styling', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const container = screen.getByText('出错了').closest('.flex');
      expect(container).toHaveClass('flex', 'items-center', 'justify-center', 'min-h-screen');
    });

    it('should have correct text center styling', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const textCenter = screen.getByText('出错了').parentElement;
      expect(textCenter).toHaveClass('text-center', 'p-8');
    });

    it('should have correct heading styling', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const heading = screen.getByText('出错了');
      expect(heading).toHaveClass('text-2xl', 'font-bold');
    });

    it('should have correct button styling', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const button = screen.getByText('刷新页面');
      expect(button).toHaveClass('px-4', 'py-2', 'bg-[var(--accent-blue)]', 'text-white', 'rounded-lg');
    });
  });

  describe('Edge Cases', () => {
    it('should handle null children', () => {
      render(
        <ErrorBoundary>
          {null}
        </ErrorBoundary>
      );
      // Should not throw error
    });

    it('should handle undefined children', () => {
      render(
        <ErrorBoundary>
          {undefined}
        </ErrorBoundary>
      );
      // Should not throw error
    });

    it('should handle empty children', () => {
      render(
        <ErrorBoundary>
          <></>
        </ErrorBoundary>
      );
      // Should not throw error
    });

    it('should handle multiple children', () => {
      render(
        <ErrorBoundary>
          <div>Child 1</div>
          <div>Child 2</div>
          <div>Child 3</div>
        </ErrorBoundary>
      );
      expect(screen.getByText('Child 1')).toBeInTheDocument();
      expect(screen.getByText('Child 2')).toBeInTheDocument();
      expect(screen.getByText('Child 3')).toBeInTheDocument();
    });

    it('should handle error with no message', () => {
      const ThrowError = () => {
        throw new Error();
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('出错了')).toBeInTheDocument();
    });

    it('should handle error with stack trace', () => {
      const ThrowError = () => {
        const error = new Error('Test error');
        error.stack = 'Error: Test error\n    at TestComponent';
        throw error;
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('出错了')).toBeInTheDocument();
    });
  });

  describe('Component Lifecycle', () => {
    it('should call componentDidCatch when error occurs', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });

    it('should update state when error occurs', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.getByText('出错了')).toBeInTheDocument();
    });
  });

  describe('Integration Tests', () => {
    it('should handle error in async component', async () => {
      const AsyncErrorComponent = () => {
        React.useEffect(() => {
          throw new Error('Async error');
        }, []);
        return <div>Async Component</div>;
      };

      render(
        <ErrorBoundary>
          <AsyncErrorComponent />
        </ErrorBoundary>
      );
      // Note: ErrorBoundary doesn't catch errors in useEffect in React 18
      // The error will be caught by the ErrorBoundary but the component won't render
      expect(screen.getByText('出错了')).toBeInTheDocument();
    });

    it('should handle error in event handler', () => {
      const ComponentWithErrorHandler = () => {
        const handleClick = () => {
          throw new Error('Handler error');
        };

        return <button onClick={handleClick}>Click me</button>;
      };

      render(
        <ErrorBoundary>
          <ComponentWithErrorHandler />
        </ErrorBoundary>
      );

      const button = screen.getByText('Click me');
      // Event handler errors are not caught by ErrorBoundary in React
      // They need to be caught with try-catch or error boundaries in the handler
      button.click();
      // The error will be logged to console but not caught by ErrorBoundary
      expect(screen.getByText('Click me')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading structure', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const heading = screen.getByRole('heading', { level: 2 });
      expect(heading).toBeInTheDocument();
    });

    it('should have accessible button', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('should render children when no error', () => {
      render(
        <ErrorBoundary>
          <div data-testid="child">Child</div>
        </ErrorBoundary>
      );
      expect(screen.getByTestId('child')).toBeInTheDocument();
    });

    it('should not render children when error occurs', () => {
      const ThrowError = () => {
        throw new Error('Test error');
      };

      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );
      expect(screen.queryByText('Child')).not.toBeInTheDocument();
    });
  });
});
