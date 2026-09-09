'use client'

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle, Clock, Activity, TrendingUp, TrendingDown } from 'lucide-react';
import api from '@/lib/api';

// 定义后端返回的指标结构（简化示例）
interface MetricItem {
  key: string;
  value: number | string;
  unit?: string;
  // 可选的彩色阈值，用于卡片颜色（如 warning/critical）
  level?: 'normal' | 'warning' | 'critical';
  trend?: 'up' | 'down' | 'stable';
}

export const DashboardCards: React.FC = () => {
  const { data, error, isLoading } = useQuery<MetricItem[]>({
    queryKey: ['metrics'],
    queryFn: async () => {
      const resp = await api.get<{ metrics: MetricItem[] }>('/api/v1/metrics');
      // 统一返回 metrics 数组；后端若返回不同结构，需要自行适配
      return resp.data.metrics;
    },
    // 30 秒自动刷新，配合后端 TTL
    refetchInterval: 30_000,
    staleTime: 20_000,
  });

  if (isLoading) return <div className="text-center text-gray-500">加载中…</div>;
  if (error) return <div className="text-center text-red-500">获取指标失败</div>;

  const getStatusIcon = (level?: string) => {
    switch (level) {
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'critical':
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      default:
        return <CheckCircle className="h-5 w-5 text-green-500" />;
    }
  };

  const getStatusColor = (level?: string) => {
    switch (level) {
      case 'warning':
        return 'bg-yellow-50 border-yellow-200';
      case 'critical':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-white border-gray-200';
    }
  };

  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'down':
        return <TrendingDown className="h-4 w-4 text-red-500" />;
      default:
        return <Activity className="h-4 w-4 text-gray-400" />;
    }
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {data?.map((item) => (
        <Card
          key={item.key}
          className={`hover:shadow-lg transition-shadow ${getStatusColor(item.level)}`}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-gray-600 flex items-center gap-2">
                {getStatusIcon(item.level)}
                <span className="truncate" title={item.key}>
                  {item.key}
                </span>
              </CardTitle>
              {item.trend && getTrendIcon(item.trend)}
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold text-gray-900">
                {item.value}
              </p>
              {item.unit && (
                <span className="text-sm font-medium text-gray-500">{item.unit}</span>
              )}
            </div>
            {item.level && (
              <div className="mt-2">
                <Badge
                  variant={
                    item.level === 'critical'
                      ? 'destructive'
                      : item.level === 'warning'
                        ? 'default'
                        : 'secondary'
                  }
                >
                  {item.level === 'critical' ? '严重' : item.level === 'warning' ? '警告' : '正常'}
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
};
