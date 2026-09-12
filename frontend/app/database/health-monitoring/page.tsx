'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { GaugeChart } from '@/components/charts/GaugeChart';
import api from '@/lib/api';

interface MonitoringStatus {
  monitoring_enabled: boolean;
  last_collection_time: string | null;
  active_alerts: number;
  total_metrics_collected: number;
  database_health: string;
  uptime_percentage: number;
}

interface HealthPayload {
  status: string;
  timestamp: string;
  metrics: {
    query_time_ms: number;
    connection_count: number;
    cache_hit_ratio: number;
    database_size_mb: number;
    slow_query_count: number | null;
    deadlock_count: number | null;
  };
  alerts: { active: number; last_24h: number };
}

interface MetricThreshold {
  metric_type: string;
  warning_threshold: number;
  critical_threshold: number;
  enabled: boolean;
  description: string;
}

const HEALTH_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  healthy: 'default',
  warning: 'secondary',
  critical: 'destructive',
  unhealthy: 'destructive',
};

export default function HealthMonitoringPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<MonitoringStatus | null>(null);
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [thresholds, setThresholds] = useState<MetricThreshold[]>([]);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [statusRes, healthRes, thresholdRes] = await Promise.all([
        api.get('/api/v1/database-monitoring/status'),
        api.get('/api/v1/database-monitoring/health'),
        api.get('/api/v1/database-monitoring/thresholds'),
      ]);
      setStatus(statusRes.data);
      setHealth(healthRes.data);
      setThresholds(Object.values(thresholdRes.data || {}));
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchAll} className="mt-2">重试</Button>
      </div>
    );
  }

  const metrics = health?.metrics;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">数据库健康监控</h1>
        <div className="flex items-center gap-3">
          <Badge variant={HEALTH_VARIANT[health?.status ?? 'healthy'] ?? 'secondary'}>
            {health?.status ?? 'unknown'}
          </Badge>
          <Button onClick={fetchAll}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader><CardTitle>可用率</CardTitle></CardHeader>
          <CardContent className="flex justify-center">
            <GaugeChart value={status?.uptime_percentage ?? 0} title="Uptime" unit="%" color="#10b981" />
          </CardContent>
        </Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">活跃告警</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-red-600">{status?.active_alerts ?? 0}</div><div className="text-xs text-gray-500 mt-1">近 24h: {health?.alerts.last_24h ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">监控采集</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{status?.total_metrics_collected ?? 0}</div><div className="text-xs text-gray-500 mt-1">{status?.monitoring_enabled ? '已启用' : '已停用'}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">缓存命中率</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{((metrics?.cache_hit_ratio ?? 0) * 100).toFixed(1)}%</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>实时指标</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><span className="text-gray-600">查询时间:</span> {metrics?.query_time_ms?.toFixed(2)} ms</div>
            <div><span className="text-gray-600">连接数:</span> {metrics?.connection_count}</div>
            <div><span className="text-gray-600">数据库大小:</span> {metrics?.database_size_mb?.toFixed(2)} MB</div>
            <div><span className="text-gray-600">慢查询:</span> {metrics?.slow_query_count ?? '—'}</div>
            <div><span className="text-gray-600">死锁:</span> {metrics?.deadlock_count ?? '—'}</div>
            <div><span className="text-gray-600">最后采集:</span> {status?.last_collection_time ? new Date(status.last_collection_time).toLocaleString() : '—'}</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>指标阈值</CardTitle></CardHeader>
        <CardContent>
          {thresholds.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无阈值配置</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-600">
                  <th className="py-2">指标</th>
                  <th className="py-2">警告阈值</th>
                  <th className="py-2">严重阈值</th>
                  <th className="py-2">状态</th>
                  <th className="py-2">说明</th>
                </tr>
              </thead>
              <tbody>
                {thresholds.map((t) => (
                  <tr key={t.metric_type} className="border-b">
                    <td className="py-2 font-mono">{t.metric_type}</td>
                    <td className="py-2">{t.warning_threshold}</td>
                    <td className="py-2">{t.critical_threshold}</td>
                    <td className="py-2">
                      <Badge variant={t.enabled ? 'default' : 'secondary'}>{t.enabled ? '启用' : '停用'}</Badge>
                    </td>
                    <td className="py-2 text-gray-500">{t.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
