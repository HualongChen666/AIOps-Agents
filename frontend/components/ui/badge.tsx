import React from 'react';

interface BadgeProps {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary';
  className?: string;
  children: React.ReactNode;
}

const variantStyles = {
  default: 'bg-blue-100 text-blue-800',
  destructive: 'bg-red-100 text-red-800',
  outline: 'border border-gray-300 text-gray-800',
  secondary: 'bg-gray-200 text-gray-800',
};

export const Badge = ({ variant = 'default', className = '', children }: BadgeProps) => {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantStyles[variant]} ${className}`}>
      {children}
    </span>
  );
};
