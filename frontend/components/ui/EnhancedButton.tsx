'use client';

import { Button as BaseButton } from '@/components/ui/button';
import { LucideIcon } from 'lucide-react';

interface EnhancedButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  icon?: LucideIcon;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
  fullWidth?: boolean;
}

export function EnhancedButton({
  children,
  variant = 'default',
  size = 'default',
  icon: Icon,
  iconPosition = 'left',
  loading = false,
  fullWidth = false,
  disabled,
  className,
  ...props
}: EnhancedButtonProps) {
  return (
    <BaseButton
      variant={variant}
      size={size}
      disabled={disabled || loading}
      className={`${fullWidth ? 'w-full' : ''} ${className || ''}`}
      {...props}
    >
      {loading ? (
        <span className="flex items-center gap-2">
          <span className="animate-spin">⟳</span>
          <span>加载中...</span>
        </span>
      ) : (
        <span className="flex items-center gap-2">
          {Icon && iconPosition === 'left' && <Icon className="h-4 w-4" />}
          {children}
          {Icon && iconPosition === 'right' && <Icon className="h-4 w-4" />}
        </span>
      )}
    </BaseButton>
  );
}