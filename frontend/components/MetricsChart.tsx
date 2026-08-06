'use client'

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

interface MetricsHistory {
  cpu?: number[];
  memory?: number[];
  net_in?: number[];
  disk?: number[];
  timestamps?: string[];
  _meta?: any;
}

const fmt = (n: number | undefined) =>
  typeof n === 'number' ? n.toFixed(1) : 'N/A';

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
      <section className="p-4 bg-[var(--color-surface)] rounded-lg shadow h-80">
        <h2 className="text-lg font-semibold mb-4">指标趋势</h2>
        <div className="text-center text-[var(--dds-gray-70)]">加载中…</div>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="p-4 bg-[var(--color-surface)] rounded-lg shadow h-80">
        <h2 className="text-lg font-semibold mb-4">指标趋势</h2>
        <div className="text-center text-[var(--dds-red-60)]">无法获取指标数据</div>
      </section>
    );
  }

  const renderSimpleChart = (values: number[] | undefined, color: string, label: string) => {
    if (!values || values.length === 0) return null;

    const numeric = values.map((v, i) => ({
      value: typeof v === 'number' ? v : 0,
      timestamp: data.timestamps?.[i] || `T${i}`,
    }));

    const valid = numeric.filter(d => typeof d.value === 'number');
    if (valid.length === 0) return null;

    const max = Math.max(...valid.map(d => d.value));
    const min = Math.min(...valid.map(d => d.value));
    const range = max - min || 1;
    const last = valid[valid.length - 1];

    return (
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-[var(--dds-slate-70)]">{label}</span>
          <span className="text-sm text-[var(--dds-gray-70)]">
            当前: {fmt(last.value)}%
          </span>
        </div>
        <div className="h-16 flex items-end gap-1">
          {valid.slice(-24).map((point, i) => {
            const height = ((point.value - min) / range) * 100;
            return (
              <div
                key={i}
                className="flex-1 rounded-t transition-all hover:opacity-80"
                style={{
                  height: `${Math.max(height, 5)}%`,
                  backgroundColor: color,
                }}
                title={`${point.timestamp}: ${fmt(point.value)}%`}
              />
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <section className="p-4 bg-[var(--color-surface)] rounded-lg shadow h-80 overflow-y-auto">
      <h2 className="text-lg font-semibold mb-4">24小时指标趋势</h2>
      <div className="space-y-4">
        {renderSimpleChart(data.cpu, '#0672cb', 'CPU 使用率')}
        {renderSimpleChart(data.memory, '#4f7d00', '内存使用率')}
        {renderSimpleChart(data.net_in, '#b85200', '网络入流量')}
        {renderSimpleChart(data.disk, '#a95adc', '磁盘使用率')}
      </div>
    </section>
  );
};
