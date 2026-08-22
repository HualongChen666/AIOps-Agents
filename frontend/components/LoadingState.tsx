'use client';

import { ReactNode } from 'react';
import { LoadingSpinner } from './LoadingSpinner';

interface LoadingStateProps {
  isLoading: boolean;
  error?: Error | null;
  children: ReactNode;
  loadingMessage?: string;
  errorMessage?: string;
  onRetry?: () => void;
}

export function LoadingState({
  isLoading,
  error,
  children,
  loadingMessage = '加载中...',
  errorMessage = '加载失败',
  onRetry,
}: LoadingStateProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[200px]">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-sm text-[var(--text-secondary)]">{loadingMessage}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[200px]">
        <div className="text-[var(--accent-red)] text-4xl mb-4">⚠️</div>
        <p className="text-sm text-[var(--text-secondary)] mb-4">{errorMessage}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-[var(--accent-blue)] text-white rounded-lg hover:bg-[var(--accent-cyan)] transition"
          >
            重试
          </button>
        )}
      </div>
    );
  }

  return <>{children}</>;
}