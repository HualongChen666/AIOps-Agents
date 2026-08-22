'use client';

import { Input as BaseInput } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { LucideIcon } from 'lucide-react';
import { useState } from 'react';

interface EnhancedInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: LucideIcon;
  iconPosition?: 'left' | 'right';
  helperText?: string;
  fullWidth?: boolean;
}

export function EnhancedInput({
  label,
  error,
  icon: Icon,
  iconPosition = 'left',
  helperText,
  fullWidth = false,
  className,
  ...props
}: EnhancedInputProps) {
  const [focused, setFocused] = useState(false);

  return (
    <div className={`space-y-1 ${fullWidth ? 'w-full' : ''}`}>
      {label && (
        <Label className={`text-sm font-medium ${error ? 'text-red-600' : 'text-gray-700'}`}>
          {label}
        </Label>
      )}
      <div className="relative">
        {Icon && iconPosition === 'left' && (
          <Icon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        )}
        <BaseInput
          className={`${Icon ? (iconPosition === 'left' ? 'pl-10' : 'pr-10') : ''} ${
            error ? 'border-red-500 focus:border-red-500' : ''
          } ${focused ? 'ring-2 ring-blue-500' : ''} ${className || ''}`}
          onFocus={(e) => {
            setFocused(true);
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            props.onBlur?.(e);
          }}
          {...props}
        />
        {Icon && iconPosition === 'right' && (
          <Icon className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        )}
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {helperText && !error && <p className="text-xs text-gray-500">{helperText}</p>}
    </div>
  );
}