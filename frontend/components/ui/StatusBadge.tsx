'use client';

import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle, Clock, AlertTriangle, HelpCircle } from 'lucide-react';

interface StatusBadgeProps {
  status: 'success' | 'error' | 'warning' | 'info' | 'pending' | 'unknown';
  text?: string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export function StatusBadge({ status, text, size = 'md', showIcon = true }: StatusBadgeProps) {
  const config = {
    success: {
      variant: 'default' as const,
      className: 'bg-green-100 text-green-800 hover:bg-green-200',
      icon: CheckCircle,
      defaultText: '成功',
    },
    error: {
      variant: 'destructive' as const,
      className: 'bg-red-100 text-red-800 hover:bg-red-200',
      icon: XCircle,
      defaultText: '失败',
    },
    warning: {
      variant: 'secondary' as const,
      className: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
      icon: AlertTriangle,
      defaultText: '警告',
    },
    info: {
      variant: 'outline' as const,
      className: 'bg-blue-100 text-blue-800 hover:bg-blue-200',
      icon: HelpCircle,
      defaultText: '信息',
    },
    pending: {
      variant: 'outline' as const,
      className: 'bg-gray-100 text-gray-800 hover:bg-gray-200',
      icon: Clock,
      defaultText: '待处理',
    },
    unknown: {
      variant: 'outline' as const,
      className: 'bg-gray-100 text-gray-800 hover:bg-gray-200',
      icon: HelpCircle,
      defaultText: '未知',
    },
  };

  const { variant, className, icon: Icon, defaultText } = config[status];
  const displayText = text || defaultText;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  };

  return (
    <Badge variant={variant} className={`${className} ${sizeClasses[size]} flex items-center gap-1`}>
      {showIcon && <Icon className="h-3 w-3" />}
      {displayText}
    </Badge>
  );
}
