'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

// The backend aggregates the in-process telemetry ring buffer
// (`core.metrics_history`) and returns per-metric statistics plus the number
// of stored data points.
interface MetricStats {
  current?: number;
  avg?: number;
  max?: number;
  min?: number;
}

interface TelemetryCoreData {
  metric_name?: string | null;
  time_range?: string;
  data_points?: number;
  metrics?: {
    cpu?: MetricStats;
    memory?: MetricStats;
    network?: MetricStats;
  };
  [key: string]: any;
}

function formatValue(value: number | undefined): string {
  return typeof value === 'number' ? value.toFixed(2) : '-';
}

function MetricCard({ title, stats, unit }: { title: string; stats?: MetricStats; unit: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        <div className="text-2xl font-bold">{formatValue(stats?.current)} {unit}</div>
        <div className="text-sm text-gray-500">平均: {formatValue(stats?.avg)} {unit}</div>
        <div className="text-sm text-gray-500">
          最小/最大: {formatValue(stats?.min)} / {formatValue(stats?.max)} {unit}
        </div>
      </CardContent>
    </Card>
  );
}

export default function TelemetryCorePage() {
  const { data: telemetryData, isLoading, error, refetch } = useQuery<TelemetryCoreData>({
    queryKey: ['monitoring-telemetry-core'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/telemetry-core');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const metrics = telemetryData?.metrics || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">遥测核心</h1>
        <Button onClick={() => refetch()}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>核心信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">指标:</span>
              <span className="font-medium">{telemetryData?.metric_name || '全部'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">时间范围:</span>
              <span className="font-medium">{telemetryData?.time_range || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">数据点数:</span>
              <span className="font-medium">{telemetryData?.data_points ?? '-'}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="CPU 使用率" stats={metrics.cpu} unit="%" />
        <MetricCard title="内存使用率" stats={metrics.memory} unit="%" />
        <MetricCard title="网络入站" stats={metrics.network} unit="MB/s" />
      </div>
    </div>
  );
}
