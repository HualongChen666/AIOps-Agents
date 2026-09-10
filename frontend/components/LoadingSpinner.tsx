import React from 'react';

type SpinnerSize = 'sm' | 'md' | 'lg';

const sizeClasses: Record<SpinnerSize, string> = {
  sm: 'w-4 h-4',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
};

export function LoadingSpinner({
  message,
  size = 'md',
  className = '',
}: {
  message?: string;
  size?: SpinnerSize;
  className?: string;
}) {
  return (
    <div className="flex items-center justify-center gap-3 w-full h-full">
      <div
        role="status"
        aria-label={message || 'Loading'}
        className={`loading-spinner rounded-full animate-spin border-2 border-t-transparent border-[var(--dds-blue-60)] ${sizeClasses[size]} ${className}`}
      />
      {message ? <div className="text-sm text-gray-600">{message}</div> : null}
    </div>
  );
}

export default LoadingSpinner;
