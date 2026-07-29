import React from 'react';

interface CardProps {
  className?: string;
  children: React.ReactNode;
  onClick?: () => void;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', children, ...props }, ref) => (
    <div
      ref={ref}
      className={`rounded-lg border border-gray-200 bg-white shadow-sm ${className}`}
      {...props}
    >
      {children}
    </div>
  )
);

Card.displayName = 'Card';

export const CardHeader = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', children, ...props }, ref) => (
    <div ref={ref} className={`flex flex-col space-y-1.5 p-6 ${className}`} {...props}>
      {children}
    </div>
  )
);

CardHeader.displayName = 'CardHeader';

export const CardTitle = React.forwardRef<HTMLParagraphElement, CardProps>(
  ({ className = '', children, ...props }, ref) => (
    <h3 ref={ref} className={`text-2xl font-semibold leading-none tracking-tight ${className}`} {...props}>
      {children}
    </h3>
  )
);

CardTitle.displayName = 'CardTitle';

export const CardContent = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', children, ...props }, ref) => (
    <div ref={ref} className={`p-6 pt-0 ${className}`} {...props}>
      {children}
    </div>
  )
);

CardContent.displayName = 'CardContent';
