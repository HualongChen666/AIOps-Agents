/**
 * Comprehensive Component Error Handling Tests
 * Tests rendering errors, state errors, and component-level error scenarios
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { LoadingState } from '@/components/LoadingState';
import { LoadingSpinner } from '@/components/LoadingSpinner';

describe('Component Error Handling', () => {
  describe('Rendering Error Handling', () => {
    it('should handle null children gracefully', () => {
      render(
        <ErrorBoundary>
          {null}
        </ErrorBoundary>
      );
      
      // Should not throw error
      expect(document.body).toBeInTheDocument();
    });

    it('should handle undefined children gracefully', () => {
      render(
        <ErrorBoundary>
          {undefined}
        </ErrorBoundary>
      );
      
      expect(document.body).toBeInTheDocument();
    });

    it('should handle empty children gracefully', () => {
      render(
        <ErrorBoundary>
          <></>
        </ErrorBoundary>
      );
      
      expect(document.body).toBeInTheDocument();
    });

    it('should handle component throwing during render', () => {
      const ThrowOnRender = () => {
        throw new Error('Render error');
      };

      render(
        <ErrorBoundary fallback={<div>Error caught</div>}>
          <ThrowOnRender />
        </ErrorBoundary>
      );

      expect(screen.getByText('Error caught')).toBeInTheDocument();
    });

    it('should handle component throwing during useEffect', () => {
      const ThrowOnEffect = () => {
        React.useEffect(() => {
          throw new Error('Effect error');
        }, []);
        return <div>Component</div>;
      };

      render(
        <ErrorBoundary fallback={<div>Error caught</div>}>
          <ThrowOnEffect />
        </ErrorBoundary>
      );

      // Note: useEffect errors are not caught by ErrorBoundary in React
      // This test documents the expected behavior
      expect(screen.getByText('Component')).toBeInTheDocument();
    });

    it('should handle component throwing during event handler', () => {
      const ThrowOnClick = () => {
        const handleClick = () => {
          throw new Error('Click error');
        };
        return <button onClick={handleClick}>Click me</button>;
      };

      render(
        <ErrorBoundary fallback={<div>Error caught</div>}>
          <ThrowOnClick />
        </ErrorBoundary>
      );

      const button = screen.getByText('Click me');
      
      // Event handler errors are not caught by ErrorBoundary
      expect(() => fireEvent.click(button)).toThrow('Click error');
    });

    it('should handle async errors in components', async () => {
      const AsyncErrorComponent = () => {
        const [error, setError] = React.useState<Error | null>(null);

        React.useEffect(() => {
          const timer = setTimeout(() => {
            setError(new Error('Async error'));
          }, 100);
          return () => clearTimeout(timer);
        }, []);

        if (error) throw error;
        return <div>Loading...</div>;
      };

      render(
        <ErrorBoundary fallback={<div>Error caught</div>}>
          <AsyncErrorComponent />
        </ErrorBoundary>
      );

      await waitFor(() => {
        expect(screen.getByText('Error caught')).toBeInTheDocument();
      });
    });

    it('should handle errors in deeply nested components', () => {
      const DeepError = () => {
        throw new Error('Deep error');
      };

      const Level3 = () => <DeepError />;
      const Level2 = () => <Level3 />;
      const Level1 = () => <Level2 />;

      render(
        <ErrorBoundary fallback={<div>Deep error caught</div>}>
          <Level1 />
        </ErrorBoundary>
      );

      expect(screen.getByText('Deep error caught')).toBeInTheDocument();
    });
  });

  describe('State Error Handling', () => {
    it('should handle invalid state updates', () => {
      const InvalidStateComponent = () => {
        const [count, setCount] = React.useState(0);

        const handleClick = () => {
          // This should not cause an error
          setCount((prev) => prev + 1);
        };

        return (
          <div>
            <span data-testid="count">{count}</span>
            <button onClick={handleClick}>Increment</button>
          </div>
        );
      };

      render(
        <ErrorBoundary>
          <InvalidStateComponent />
        </ErrorBoundary>
      );

      const button = screen.getByText('Increment');
      fireEvent.click(button);

      expect(screen.getByTestId('count')).toHaveTextContent('1');
    });

    it('should handle state updates after unmount', () => {
      const StateAfterUnmount = () => {
        const [mounted, setMounted] = React.useState(true);
        const [count, setCount] = React.useState(0);

        React.useEffect(() => {
          const timer = setTimeout(() => {
            setCount(1);
          }, 100);
          return () => clearTimeout(timer);
        }, []);

        if (!mounted) return null;

        return (
          <div>
            <span data-testid="count">{count}</span>
            <button onClick={() => setMounted(false)}>Unmount</button>
          </div>
        );
      };

      render(
        <ErrorBoundary>
          <StateAfterUnmount />
        </ErrorBoundary>
      );

      const button = screen.getByText('Unmount');
      fireEvent.click(button);

      // Component unmounts without error
      expect(screen.queryByTestId('count')).not.toBeInTheDocument();
    });

    it('should handle memory leaks in state updates', () => {
      let setCount: React.Dispatch<React.SetStateAction<number>>;

      const MemoryLeakComponent = () => {
        const [count, _setCount] = React.useState(0);
        setCount = _setCount;

        return <div data-testid="component">Component</div>;
      };

      const { unmount } = render(
        <ErrorBoundary>
          <MemoryLeakComponent />
        </ErrorBoundary>
      );

      unmount();

      // This would cause a warning in development but not an error
      expect(() => setCount(1)).not.toThrow();
    });

    it('should handle concurrent state updates', () => {
      const ConcurrentStateComponent = () => {
        const [count, setCount] = React.useState(0);

        const handleClick = () => {
          setCount((prev) => prev + 1);
          setCount((prev) => prev + 1);
          setCount((prev) => prev + 1);
        };

        return (
          <div>
            <span data-testid="count">{count}</span>
            <button onClick={handleClick}>Increment 3x</button>
          </div>
        );
      };

      render(
        <ErrorBoundary>
          <ConcurrentStateComponent />
        </ErrorBoundary>
      );

      const button = screen.getByText('Increment 3x');
      fireEvent.click(button);

      expect(screen.getByTestId('count')).toHaveTextContent('3');
    });
  });

  describe('LoadingState Component Error Handling', () => {
    it('should display loading state when isLoading is true', () => {
      render(
        <LoadingState isLoading={true}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('加载中...')).toBeInTheDocument();
      expect(screen.queryByText('Content')).not.toBeInTheDocument();
    });

    it('should display error state when error is provided', () => {
      const error = new Error('Test error');
      const onRetry = jest.fn();

      render(
        <LoadingState isLoading={false} error={error} onRetry={onRetry}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('加载失败')).toBeInTheDocument();
      expect(screen.getByText('重试')).toBeInTheDocument();
      expect(screen.queryByText('Content')).not.toBeInTheDocument();
    });

    it('should display custom error message', () => {
      const error = new Error('Test error');

      render(
        <LoadingState isLoading={false} error={error} errorMessage="Custom error message">
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Custom error message')).toBeInTheDocument();
    });

    it('should call onRetry when retry button is clicked', () => {
      const error = new Error('Test error');
      const onRetry = jest.fn();

      render(
        <LoadingState isLoading={false} error={error} onRetry={onRetry}>
          <div>Content</div>
        </LoadingState>
      );

      const retryButton = screen.getByText('重试');
      fireEvent.click(retryButton);

      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it('should not display retry button when onRetry is not provided', () => {
      const error = new Error('Test error');

      render(
        <LoadingState isLoading={false} error={error}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.queryByText('重试')).not.toBeInTheDocument();
    });

    it('should display custom loading message', () => {
      render(
        <LoadingState isLoading={true} loadingMessage="Custom loading message">
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Custom loading message')).toBeInTheDocument();
    });

    it('should display children when not loading and no error', () => {
      render(
        <LoadingState isLoading={false}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Content')).toBeInTheDocument();
      expect(screen.queryByText('加载中...')).not.toBeInTheDocument();
    });

    it('should handle null error gracefully', () => {
      render(
        <LoadingState isLoading={false} error={null}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should handle undefined error gracefully', () => {
      render(
        <LoadingState isLoading={false} error={undefined}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('should handle error with message', () => {
      const error = new Error('Detailed error message');

      render(
        <LoadingState isLoading={false} error={error}>
          <div>Content</div>
        </LoadingState>
      );

      expect(screen.getByText('加载失败')).toBeInTheDocument();
    });
  });

  describe('LoadingSpinner Component Error Handling', () => {
    it('should render with default size', () => {
      render(<LoadingSpinner />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-8', 'h-8');
    });

    it('should render with small size', () => {
      render(<LoadingSpinner size="sm" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-4', 'h-4');
    });

    it('should render with large size', () => {
      render(<LoadingSpinner size="lg" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('w-12', 'h-12');
    });

    it('should render with custom className', () => {
      render(<LoadingSpinner className="custom-class" />);
      const spinner = document.querySelector('.loading-spinner');
      expect(spinner).toHaveClass('custom-class');
    });

    it('should handle invalid size prop gracefully', () => {
      // @ts-ignore - testing invalid prop
      render(<LoadingSpinner size="invalid" />);
      const spinner = document.querySelector('.loading-spinner');
      // Should not throw error
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Component Lifecycle Error Handling', () => {
    it('should handle errors in constructor', () => {
      class ErrorInConstructor extends React.Component {
        constructor(props: any) {
          super(props);
          throw new Error('Constructor error');
        }

        render() {
          return <div>Component</div>;
        }
      }

      render(
        <ErrorBoundary fallback={<div>Constructor error caught</div>}>
          <ErrorInConstructor />
        </ErrorBoundary>
      );

      expect(screen.getByText('Constructor error caught')).toBeInTheDocument();
    });

    it('should handle errors in componentDidMount', () => {
      class ErrorInDidMount extends React.Component {
        componentDidMount() {
          throw new Error('DidMount error');
        }

        render() {
          return <div>Component</div>;
        }
      }

      render(
        <ErrorBoundary fallback={<div>DidMount error caught</div>}>
          <ErrorInDidMount />
        </ErrorBoundary>
      );

      // componentDidMount errors are not caught by ErrorBoundary
      expect(screen.getByText('Component')).toBeInTheDocument();
    });

    it('should handle errors in componentDidUpdate', () => {
      class ErrorInDidUpdate extends React.Component {
        state = { count: 0 };

        componentDidUpdate() {
          if (this.state.count === 1) {
            throw new Error('DidUpdate error');
          }
        }

        render() {
          return (
            <div>
              <span data-testid="count">{this.state.count}</span>
              <button onClick={() => this.setState({ count: 1 })}>Update</button>
            </div>
          );
        }
      }

      render(
        <ErrorBoundary fallback={<div>DidUpdate error caught</div>}>
          <ErrorInDidUpdate />
        </ErrorBoundary>
      );

      const button = screen.getByText('Update');
      
      // componentDidUpdate errors are not caught by ErrorBoundary
      expect(() => fireEvent.click(button)).toThrow('DidUpdate error');
    });

    it('should handle errors in componentWillUnmount', () => {
      class ErrorInWillUnmount extends React.Component {
        componentWillUnmount() {
          throw new Error('WillUnmount error');
        }

        render() {
          return <div>Component</div>;
        }
      }

      const { unmount } = render(
        <ErrorBoundary fallback={<div>WillUnmount error caught</div>}>
          <ErrorInWillUnmount />
        </ErrorBoundary>
      );

      // componentWillUnmount errors are not caught by ErrorBoundary
      expect(() => unmount()).toThrow('WillUnmount error');
    });

    it('should handle errors in getDerivedStateFromProps', () => {
      class ErrorInGetDerivedState extends React.Component {
        state = { value: 0 };

        static getDerivedStateFromProps(props: any, state: any) {
          if (props.shouldError) {
            throw new Error('GetDerivedState error');
          }
          return null;
        }

        render() {
          return <div>Component</div>;
        }
      }

      render(
        <ErrorBoundary fallback={<div>GetDerivedState error caught</div>}>
          <ErrorInGetDerivedState shouldError={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText('GetDerivedState error caught')).toBeInTheDocument();
    });
  });

  describe('Props Error Handling', () => {
    it('should handle missing required props gracefully', () => {
      const ComponentWithRequiredProps = ({ name }: { name: string }) => {
        return <div>Hello {name}</div>;
      };

      // @ts-ignore - testing missing prop
      render(<ComponentWithRequiredProps />);
      
      // Component renders without error (TypeScript would catch this at compile time)
      expect(screen.getByText('Hello undefined')).toBeInTheDocument();
    });

    it('should handle null props gracefully', () => {
      const ComponentWithProps = ({ name }: { name: string | null }) => {
        return <div>Hello {name || 'World'}</div>;
      };

      render(<ComponentWithProps name={null} />);
      
      expect(screen.getByText('Hello World')).toBeInTheDocument();
    });

    it('should handle undefined props gracefully', () => {
      const ComponentWithProps = ({ name }: { name?: string }) => {
        return <div>Hello {name || 'World'}</div>;
      };

      render(<ComponentWithProps />);
      
      expect(screen.getByText('Hello World')).toBeInTheDocument();
    });

    it('should handle invalid prop types gracefully', () => {
      const ComponentWithNumberProp = ({ count }: { count: number }) => {
        return <div>Count: {count}</div>;
      };

      // @ts-ignore - testing invalid prop type
      render(<ComponentWithNumberProp count="invalid" />);
      
      // Component renders without error (TypeScript would catch this at compile time)
      expect(screen.getByText('Count: invalid')).toBeInTheDocument();
    });

    it('should handle array props with errors', () => {
      const ComponentWithArrayProp = ({ items }: { items: string[] }) => {
        return (
          <div>
            {items.map((item, index) => (
              <span key={index}>{item}</span>
            ))}
          </div>
        );
      };

      render(<ComponentWithArrayProp items={['a', 'b', 'c']} />);
      
      expect(screen.getByText('a')).toBeInTheDocument();
      expect(screen.getByText('b')).toBeInTheDocument();
      expect(screen.getByText('c')).toBeInTheDocument();
    });

    it('should handle object props with errors', () => {
      const ComponentWithObjectProp = ({ user }: { user: { name: string } }) => {
        return <div>Name: {user.name}</div>;
      };

      render(<ComponentWithObjectProp user={{ name: 'John' }} />);
      
      expect(screen.getByText('Name: John')).toBeInTheDocument();
    });
  });

  describe('Context Error Handling', () => {
    it('should handle missing context gracefully', () => {
      const TestContext = React.createContext<string | undefined>(undefined);

      const ConsumerComponent = () => {
        const value = React.useContext(TestContext);
        return <div>Value: {value || 'default'}</div>;
      };

      render(
        <TestContext.Provider value={undefined}>
          <ConsumerComponent />
        </TestContext.Provider>
      );

      expect(screen.getByText('Value: default')).toBeInTheDocument();
    });

    it('should handle context provider errors', () => {
      const TestContext = React.createContext<string>('default');

      const ErrorProvider = ({ children }: { children: React.ReactNode }) => {
        throw new Error('Provider error');
      };

      render(
        <ErrorBoundary fallback={<div>Provider error caught</div>}>
          <ErrorProvider>
            <TestContext.Provider value="test">
              <div>Child</div>
            </TestContext.Provider>
          </ErrorProvider>
        </ErrorBoundary>
      );

      expect(screen.getByText('Provider error caught')).toBeInTheDocument();
    });
  });

  describe('Ref Error Handling', () => {
    it('should handle null ref gracefully', () => {
      const ComponentWithRef = () => {
        const ref = React.useRef<HTMLDivElement>(null);

        return <div ref={ref}>Component</div>;
      };

      render(<ComponentWithRef />);
      
      expect(screen.getByText('Component')).toBeInTheDocument();
    });

    it('should handle ref callback errors', () => {
      const ComponentWithRefCallback = () => {
        const setRef = React.useCallback((node: HTMLDivElement | null) => {
          if (node) {
            // Simulate error in ref callback
            // This should not crash the component
            node.focus();
          }
        }, []);

        return <div ref={setRef}>Component</div>;
      };

      render(<ComponentWithRefCallback />);
      
      expect(screen.getByText('Component')).toBeInTheDocument();
    });
  });

  describe('Error Recovery', () => {
    it('should allow recovery after error with key change', () => {
      const ErrorComponent = ({ shouldError }: { shouldError: boolean }) => {
        if (shouldError) {
          throw new Error('Component error');
        }
        return <div>Recovered</div>;
      };

      const { rerender } = render(
        <ErrorBoundary fallback={<div>Error</div>} key="boundary1">
          <ErrorComponent shouldError={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText('Error')).toBeInTheDocument();

      rerender(
        <ErrorBoundary fallback={<div>Error</div>} key="boundary2">
          <ErrorComponent shouldError={false} />
        </ErrorBoundary>
      );

      expect(screen.getByText('Recovered')).toBeInTheDocument();
    });

    it('should handle error boundary reset with state change', () => {
      const ResettableErrorBoundary = ({ children, resetKey }: { children: React.ReactNode; resetKey: number }) => {
        const [hasError, setHasError] = React.useState(false);
        const [error, setError] = React.useState<Error | null>(null);

        React.useEffect(() => {
          setHasError(false);
          setError(null);
        }, [resetKey]);

        if (hasError) {
          return <div>Error: {error?.message}</div>;
        }

        return (
          <ErrorBoundary
            fallback={<div>Error caught</div>}
            onError={(err) => {
              setHasError(true);
              setError(err);
            }}
          >
            {children}
          </ErrorBoundary>
        );
      };

      const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
        if (shouldThrow) throw new Error('Test error');
        return <div>No error</div>;
      };

      const { rerender } = render(
        <ResettableErrorBoundary resetKey={1}>
          <ThrowError shouldThrow={true} />
        </ResettableErrorBoundary>
      );

      expect(screen.getByText('Error caught')).toBeInTheDocument();

      rerender(
        <ResettableErrorBoundary resetKey={2}>
          <ThrowError shouldThrow={false} />
        </ResettableErrorBoundary>
      );

      expect(screen.getByText('No error')).toBeInTheDocument();
    });
  });
});
