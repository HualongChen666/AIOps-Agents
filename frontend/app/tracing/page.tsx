'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Search, RefreshCw, Activity, Clock, AlertTriangle, CheckCircle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface Trace {
  trace_id: string;
  root_service: string;
  operation: string;
  duration_ms: number;
  status: string;
  timestamp: string;
  span_count?: number;
  error_count?: number;
}

interface TraceDetail {
  trace_id: string;
  spans: Array<{
    span_id: string;
    parent_id: string | null;
    service: string;
    operation: string;
    start_time: string;
    duration_ms: number;
    status: string;
    tags: Record<string, any>;
  }>;
  services: string[];
  total_duration_ms: number;
  error_count: number;
}

export default function TracingPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  // 🔧 获取追踪列表
  const { data: tracesData, isLoading, error, refetch } = useQuery<{ traces: Trace[] }>({
    queryKey: ['tracing-traces'],
    queryFn: async () => {
      const resp = await api.get('/api/tracing/traces?limit=50');
      return resp.data;
    },
    refetchInterval: 15000, // 15秒刷新
  });

  // 🔧 获取追踪详情
  const { data: traceDetailData, isLoading: detailLoading, refetch: refetchDetail } = useQuery<TraceDetail>({
    queryKey: ['tracing-detail', selectedTrace?.trace_id],
    queryFn: async () => {
      const resp = await api.get(`/api/tracing/trace/${selectedTrace?.trace_id}`);
      return resp.data;
    },
    enabled: !!selectedTrace,
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(isLoading || detailLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (error) {
      showError('Failed to load tracing data');
      setPageError(error as Error);
    }
  }, [error, showError, setPageError]);

  const traces = tracesData?.traces || [];
  const traceDetail = traceDetailData || null;

  const filteredTraces = traces.filter((trace) => {
    if (searchQuery && !trace.trace_id.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !trace.root_service.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !trace.operation.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  const traceColumns = [
    { key: 'trace_id' as const, label: '追踪ID' },
    { key: 'root_service' as const, label: '服务' },
    { key: 'operation' as const, label: '操作' },
    { key: 'duration_ms' as const, label: '持续时间', render: (value: number) => `${value.toFixed(2)}ms` },
    { key: 'status' as const, label: '状态', render: (value: string) => (
      <StatusBadge status={value === 'ok' ? 'success' : value === 'error' ? 'error' : 'warning'} text={value} />
    )},
    { key: 'timestamp' as const, label: '时间', render: (value: string) => new Date(value).toLocaleString() },
  ];

  const spanColumns = [
    { key: 'span_id' as const, label: 'Span ID' },
    { key: 'service' as const, label: '服务' },
    { key: 'operation' as const, label: '操作' },
    { key: 'duration_ms' as const, label: '持续时间', render: (value: number) => `${value.toFixed(2)}ms` },
    { key: 'status' as const, label: '状态', render: (value: string) => (
      <StatusBadge status={value === 'ok' ? 'success' : 'error'} text={value} />
    )},
  ];

  const handleTraceClick = (trace: Trace) => {
    setSelectedTrace(trace);
    setShowDetailModal(true);
  };

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
          description="无法加载追踪数据，请稍后重试"
          action={<Button onClick={() => refetch()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetch()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  const avgDuration = traces.length > 0 ? traces.reduce((sum, t) => sum + t.duration_ms, 0) / traces.length : 0;
  const errorRate = traces.length > 0 ? (traces.filter((t) => t.status === 'error').length / traces.length) * 100 : 0;
  const totalTraces = traces.length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">链路追踪</h1>
            <p className="text-sm text-gray-500">分布式链路追踪和性能分析</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetch()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总追踪数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{totalTraces}</p>
            <p className="text-sm text-gray-500 mt-1">总追踪记录</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均持续时间</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{avgDuration.toFixed(2)}ms</p>
            <p className="text-sm text-gray-500 mt-1">平均响应时间</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">错误率</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${errorRate > 5 ? 'text-red-600' : 'text-green-600'}`}>
              {errorRate.toFixed(1)}%
            </p>
            <p className="text-sm text-gray-500 mt-1">错误追踪占比</p>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索追踪ID、服务或操作"
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Traces List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            追踪列表 ({filteredTraces.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredTraces.length === 0 ? (
            <EmptyState
              title="暂无追踪数据"
              description="当前没有可用的链路追踪数据"
            />
          ) : (
            <DataTable
              data={filteredTraces}
              columns={traceColumns}
              pageSize={15}
              emptyMessage="暂无追踪数据"
              onRowClick={handleTraceClick}
            />
          )}
        </CardContent>
      </Card>

      {/* Trace Detail Modal */}
      {selectedTrace && (
        <Card className="hidden">
          <CardHeader>
            <CardTitle>追踪详情</CardTitle>
          </CardHeader>
          <CardContent>
            {detailLoading ? (
              <LoadingSpinner />
            ) : traceDetail ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700">追踪ID</label>
                    <p className="text-gray-900">{traceDetail.trace_id}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">总持续时间</label>
                    <p className="text-gray-900">{traceDetail.total_duration_ms.toFixed(2)}ms</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">服务数</label>
                    <p className="text-gray-900">{traceDetail.services.length}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">错误数</label>
                    <p className="text-gray-900">{traceDetail.error_count}</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-4">Span列表</h3>
                  <DataTable
                    data={traceDetail.spans}
                    columns={spanColumns}
                    pageSize={10}
                    emptyMessage="暂无Span数据"
                  />
                </div>
              </div>
            ) : (
              <EmptyState title="暂无详情数据" description="无法加载追踪详情" />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}