import React from 'react';

export function LoadingSpinner({ message }: { message?: string }) {
  return (
    <div className="flex items-center justify-center w-full h-full">
      <div className="flex items-center gap-3">
        <div className="w-6 h-6 rounded-full animate-spin border-2 border-t-transparent border-[var(--dds-blue-60)]" />
        {message ? <div className="text-sm text-gray-600">{message}</div> : null}
      </div>
    </div>
  );
}

export default LoadingSpinner;
