import React from 'react';

interface ProgressProps {
  value?: number;
  className?: string;
}

export const Progress = ({ value = 0, className = '' }: ProgressProps) => {
  return (
    <div className={`relative h-4 w-full overflow-hidden rounded-full bg-gray-200 ${className}`}>
      <div
        className="h-full bg-blue-600 transition-all duration-300"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
};
