'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: LucideIcon;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: number;
  level?: 'normal' | 'warning' | 'critical';
  description?: string;
  onClick?: () => void;
}

export function KpiCard({
  title,
  value,
  unit,
  icon: Icon,
  trend,
  trendValue,
  level = 'normal',
  description,
  onClick,
}: KpiCardProps) {
  const getLevelColor = () => {
    switch (level) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'normal':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return '↑';
      case 'down':
        return '↓';
      case 'stable':
        return '→';
      default:
        return '';
    }
  };

  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return 'text-red-500';
      case 'down':
        return 'text-green-500';
      case 'stable':
        return 'text-gray-500';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <Card className={`hover:shadow-md transition cursor-pointer ${onClick ? 'hover:border-blue-300' : ''}`} onClick={onClick}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {Icon && <Icon className="h-5 w-5 text-[var(--accent-cyan)]" />}
            <CardTitle className="text-sm font-medium text-gray-700">{title}</CardTitle>
          </div>
          <Badge className={getLevelColor()} variant="outline">
            {level === 'critical' ? '严重' : level === 'warning' ? '警告' : '正常'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <span className={`text-3xl font-bold ${level === 'critical' ? 'text-red-600' : level === 'warning' ? 'text-yellow-600' : 'text-green-600'}`}>
            {value}
          </span>
          {unit && <span className="text-sm text-gray-500">{unit}</span>}
        </div>
        {description && <p className="text-xs text-gray-500 mt-1">{description}</p>}
        {trend && trendValue !== undefined && (
          <div className="flex items-center gap-1 mt-2 text-xs">
            <span className={getTrendColor()}>{getTrendIcon()}</span>
            <span className="text-gray-500">
              {trend === 'up' ? '上升' : trend === 'down' ? '下降' : '稳定'} {Math.abs(trendValue)}%
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}