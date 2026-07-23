'use client'

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

// 定义后端返回的指标结构（简化示例）
interface MetricItem {
  key: string;
  value: number | string;
  unit?: string;
  // 可选的彩色阈值，用于卡片颜色（如 warning/critical）
  level?: 'normal' | 'warning' | 'critical';
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

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {data?.map((item) => (
        <div
          key={item.key}
          className={`p-4 rounded shadow-sm border ${
            item.level === 'warning'
              ? 'border-yellow-300 bg-yellow-50'
              : item.level === 'critical'
              ? 'border-red-300 bg-red-50'
              : 'border-gray-200 bg-white'
          }`}
        >
          <h3 className="text-sm font-medium text-gray-600 truncate" title={item.key}>
            {item.key}
          </h3>
          <p className="mt-2 text-2xl font-semibold text-gray-800">
            {item.value}
            {item.unit && <span className="text-base font-medium">{item.unit}</span>}
          </p>
        </div>
      ))}
    </div>
  );
};
