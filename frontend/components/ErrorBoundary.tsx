'use client';

import { Component, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  /** Invoked when a descendant throws, for logging/reporting. */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  /**
   * How the default fallback's refresh button reloads the page. Injectable because
   * `window.location.reload` is a non-configurable property in jsdom and therefore
   * cannot be spied on in tests.
   */
  reloadPage?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const reloadPage =
        this.props.reloadPage ??
        (() => {
          if (typeof window !== 'undefined') {
            window.location.reload();
          }
        });

      return (
        <div className="flex items-center justify-center min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
          <div className="text-center p-8">
            <h2 className="text-2xl font-bold text-[var(--accent-red)] mb-4">出错了</h2>
            <p className="text-[var(--text-secondary)] mb-4">页面加载失败，请刷新重试</p>
            <button
              onClick={reloadPage}
              className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg hover:bg-[var(--accent-cyan)] transition"
            >
              刷新页面
            </button>
            {this.state.error && (
              <details className="mt-4 text-left">
                <summary className="cursor-pointer text-sm text-[var(--text-muted)]">错误详情</summary>
                <pre className="mt-2 p-4 bg-[var(--bg-card)] rounded text-xs text-[var(--text-secondary)] overflow-auto">
                  {this.state.error.toString()}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}