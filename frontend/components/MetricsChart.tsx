'use client'

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

interface MetricDataPoint {
  timestamp: string;
  value: number;
}

interface MetricsHistory {
  cpu: MetricDataPoint[];
  memory: MetricDataPoint[];
  disk: MetricDataPoint[];
}

export const MetricsChart: React.FC = () => {
  const { data, isLoading, error } = useQuery<MetricsHistory>({
    queryKey: ['metrics-history'],
    queryFn: async () => {
      const resp = await api.get<MetricsHistory>('/api/v1/metrics/history?hours=24');
      return resp.data;
    },
    refetchInterval: 60_000,
  });

  if (isLoading) {
    return (
      <section className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow h-80">
        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          指标趋势
        </h2>
        <div className="text-center text-gray-500">加载中…</div>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow h-80">
        <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          指标趋势
        </h2>
        <div className="text-center text-red-500">无法获取指标数据</div>
      </section>
    );
  }

  const renderSimpleChart = (data: MetricDataPoint[], color: string, label: string) => {
    if (!data || data.length === 0) return null;

    const max = Math.max(...data.map(d => d.value));
    const min = Math.min(...data.map(d => d.value));
    const range = max - min || 1;

    return (
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            当前: {data[data.length - 1]?.value.toFixed(1)}%
          </span>
        </div>
        <div className="h-16 flex items-end gap-1">
          {data.slice(-24).map((point, i) => {
            const height = ((point.value - min) / range) * 100;
            return (
              <div
                key={i}
                className="flex-1 rounded-t transition-all hover:opacity-80"
                style={{
                  height: `${Math.max(height, 5)}%`,
                  backgroundColor: color,
                }}
                title={`${point.timestamp}: ${point.value.toFixed(1)}%`}
              />
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <section className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow h-80 overflow-y-auto">
      <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
        24小时指标趋势
      </h2>
      
      <div className="space-y-4">
        {renderSimpleChart(data.cpu, '#3b82f6', 'CPU 使用率')}
        {renderSimpleChart(data.memory, '#10b981', '内存使用率')}
        {renderSimpleChart(data.disk, '#f59e0b', '磁盘使用率')}
      </div>
    </section>
  );
};
