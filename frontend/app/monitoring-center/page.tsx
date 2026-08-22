'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { KpiCard } from '@/components/ui/KpiCard';
import { DataTable } from '@/components/ui/DataTable';
import { GaugeChart } from '@/components/charts/GaugeChart';
import { TrendChart } from '@/components/charts/TrendChart';
import { Activity, RefreshCw, Search, Filter, Zap, Cpu, HardDrive, Network } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface MetricsSnapshot {
  cpu?: { usage_percent: number };
  memory?: { usage_percent: number };
  disk?: { usage_percent: number };
  network?: { in_bytes: number; out_bytes: number };
}

interface APMHealth {
  application: string;
  version: string;
  health_status: { status: string; checks: Record<string, any> };
  timestamp: string;
}

interface Trace {
  trace_id: string;
  root_service: string;
  operation: string;
  duration_ms: number;
  status: string;
  timestamp: string;
}

export default function MonitoringCenterPage() {
  const [activeTab, setActiveTab] = useState<'metrics' | 'tracing' | 'apm'>('metrics');
  const [timeRange, setTimeRange] = useState('1h');

  // 🔧 获取系统指标
  const { data: metricsData, isLoading: metricsLoading, error: metricsError, refetch: refetchMetrics } = useQuery<MetricsSnapshot>({
    queryKey: ['metrics-snapshot', timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/metrics/');
      return resp.data.snapshot || {};
    },
    refetchInterval: 5000, // 5秒刷新
  });

  // 🔧 获取APM健康状态
  const { data: apmData, isLoading: apmLoading, error: apmError, refetch: refetchAPM } = useQuery<APMHealth>({
    queryKey: ['apm-health'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/apm/health');
      return resp.data;
    },
    refetchInterval: 30000, // 30秒刷新
  });

  // 🔧 获取追踪数据
  const { data: tracesData, isLoading: tracesLoading, error: tracesError, refetch: refetchTraces } = useQuery<{ traces: Trace[] }>({
    queryKey: ['tracing-traces'],
    queryFn: async () => {
      const resp = await api.get('/api/tracing/traces?limit=20');
      return resp.data;
    },
    refetchInterval: 15000, // 15秒刷新
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(metricsLoading || apmLoading || tracesLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (metricsError) {
      showError('Failed to load metrics data');
      setPageError(metricsError as Error);
    }
    if (apmError) {
      showError('Failed to load APM data');
      setPageError(apmError as Error);
    }
    if (tracesError) {
      showError('Failed to load tracing data');
      setPageError(tracesError as Error);
    }
  }, [metricsError, apmError, tracesError, showError, setPageError]);

  const metrics = metricsData || {};
  const apmHealth: APMHealth = apmData || { application: '', version: '', health_status: { status: '', checks: {} }, timestamp: '' };
  const traces = tracesData?.traces || [];

  const cpuUsage = metrics.cpu?.usage_percent || 0;
  const memoryUsage = metrics.memory?.usage_percent || 0;
  const diskUsage = metrics.disk?.usage_percent || 0;

  const traceColumns = [
    { key: 'trace_id' as const, label: '追踪ID' },
    { key: 'root_service' as const, label: '服务' },
    { key: 'operation' as const, label: '操作' },
    { key: 'duration_ms' as const, label: '持续时间', render: (value: number) => `${value.toFixed(2)}ms` },
    { key: 'status' as const, label: '状态' },
    { key: 'timestamp' as const, label: '时间', render: (value: string) => new Date(value).toLocaleString() },
  ];

  // 🔧 P1 Integration: Use enhanced loading and empty states
  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载监控数据，请稍后重试"
          action={<Button onClick={() => { refetchMetrics(); refetchAPM(); refetchTraces(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => { refetchMetrics(); refetchAPM(); refetchTraces(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">监控中心</h1>
            <p className="text-sm text-gray-500">系统性能、APM和链路追踪监控</p>
          </div>
        </div>
        <div className="flex gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-3 py-2 border rounded-md bg-white"
          >
            <option value="5m">5分钟</option>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
          </select>
          <Button onClick={() => { refetchMetrics(); refetchAPM(); refetchTraces(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'metrics' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('metrics')}
        >
          <Zap className="h-4 w-4 mr-2" />
          系统指标
        </Button>
        <Button
          variant={activeTab === 'tracing' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('tracing')}
        >
          <Search className="h-4 w-4 mr-2" />
          链路追踪
        </Button>
        <Button
          variant={activeTab === 'apm' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('apm')}
        >
          <Activity className="h-4 w-4 mr-2" />
          APM监控
        </Button>
      </div>

      {/* Metrics Tab */}
      {activeTab === 'metrics' && (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <KpiCard
              title="CPU使用率"
              value={cpuUsage.toFixed(1)}
              unit="%"
              icon={Cpu}
              level={cpuUsage > 90 ? 'critical' : cpuUsage > 70 ? 'warning' : 'normal'}
              description="处理器使用率"
            />
            <KpiCard
              title="内存使用率"
              value={memoryUsage.toFixed(1)}
              unit="%"
              icon={HardDrive}
              level={memoryUsage > 90 ? 'critical' : memoryUsage > 70 ? 'warning' : 'normal'}
              description="内存使用率"
            />
            <KpiCard
              title="磁盘使用率"
              value={diskUsage.toFixed(1)}
              unit="%"
              icon={HardDrive}
              level={diskUsage > 90 ? 'critical' : diskUsage > 70 ? 'warning' : 'normal'}
              description="磁盘使用率"
            />
          </div>

          {/* Gauge Charts */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <GaugeChart
              value={cpuUsage}
              min={0}
              max={100}
              title="CPU使用率"
              color={cpuUsage > 90 ? '#ef4444' : cpuUsage > 70 ? '#f59e0b' : '#10b981'}
            />
            <GaugeChart
              value={memoryUsage}
              min={0}
              max={100}
              title="内存使用率"
              color={memoryUsage > 90 ? '#ef4444' : memoryUsage > 70 ? '#f59e0b' : '#10b981'}
            />
            <GaugeChart
              value={diskUsage}
              min={0}
              max={100}
              title="磁盘使用率"
              color={diskUsage > 90 ? '#ef4444' : diskUsage > 70 ? '#f59e0b' : '#10b981'}
            />
          </div>

          {/* Network Metrics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-5 w-5" />
                网络流量
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700">入站流量</label>
                  <p className="text-2xl font-bold text-gray-900">
                    {((metrics.network?.in_bytes || 0) / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">出站流量</label>
                  <p className="text-2xl font-bold text-gray-900">
                    {((metrics.network?.out_bytes || 0) / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Tracing Tab */}
      {activeTab === 'tracing' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              链路追踪
            </CardTitle>
          </CardHeader>
          <CardContent>
            {traces.length === 0 ? (
              <EmptyState
                title="暂无追踪数据"
                description="当前没有可用的链路追踪数据"
              />
            ) : (
              <DataTable
                data={traces}
                columns={traceColumns}
                pageSize={15}
                emptyMessage="暂无追踪数据"
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* APM Tab */}
      {activeTab === 'apm' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                应用健康状态
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">应用名称</span>
                  <span className="text-sm font-medium text-gray-900">{apmHealth.application || 'aiops-agent'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">版本</span>
                  <span className="text-sm font-medium text-gray-900">{apmHealth.version || '1.0.0'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">健康状态</span>
                  <span className={`text-sm font-medium ${apmHealth.health_status?.status === 'healthy' ? 'text-green-600' : 'text-red-600'
                    }`}>
                    {apmHealth.health_status?.status || 'unknown'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">最后更新</span>
                  <span className="text-sm text-gray-500">
                    {apmHealth.timestamp ? new Date(apmHealth.timestamp).toLocaleString() : '-'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>健康检查</CardTitle>
            </CardHeader>
            <CardContent>
              {apmHealth.health_status?.checks ? (
                <div className="space-y-2">
                  {Object.entries(apmHealth.health_status.checks).map(([checkName, checkResult]: [string, any]) => (
                    <div key={checkName} className="flex items-center justify-between p-3 border rounded">
                      <span className="text-sm font-medium text-gray-700">{checkName}</span>
                      <span className={`text-sm ${checkResult?.status === 'healthy' ? 'text-green-600' : 'text-red-600'
                        }`}>
                        {checkResult?.status || 'unknown'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="暂无健康检查数据"
                  description="当前没有可用的健康检查信息"
                />
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}