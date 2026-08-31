'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Search, RefreshCw, Activity, Clock, AlertTriangle, CheckCircle, Layers, Network, BarChart3, Plus, Trash2, Edit, Filter, TrendingUp, Zap, Database, Download, ChevronRight, ChevronDown, GitBranch, Flame, Calendar, ArrowUpDown, X } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

// ============================================================
// Type Definitions
// ============================================================

interface Trace {
  trace_id: string;
  root_service: string;
  operation: string;
  duration_ms: number;
  status: string;
  timestamp: string;
  span_count?: number;
  error_count?: number;
  tags?: Record<string, any>;
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

interface Span {
  span_id: string;
  trace_id: string;
  parent_id: string | null;
  service: string;
  operation: string;
  start_time: string;
  duration_ms: number;
  status: string;
  tags: Record<string, any>;
}

interface Service {
  name: string;
  type: string;
  version: string;
  metadata: Record<string, any>;
}

interface Operation {
  id: string;
  name: string;
  service: string;
  type: string;
  metadata: Record<string, any>;
}

interface Analytics {
  id: string;
  service: string;
  operation: string | null;
  metric_type: string;
  value: number;
  timestamp: string;
}

interface PerformanceMetrics {
  time_range: string;
  granularity: string;
  service: string | null;
  operation: string | null;
  metrics: {
    avg_duration_ms: number;
    p50_duration_ms: number;
    p95_duration_ms: number;
    p99_duration_ms: number;
    max_duration_ms: number;
    min_duration_ms: number;
    error_count: number;
    error_rate: number;
    throughput_per_hour: number;
  };
  time_series: Array<{
    timestamp: string;
    avg_duration: number;
    error_rate: number;
    throughput: number;
  }>;
  total_traces: number;
}

interface ServiceDependency {
  service: string;
  depends_on: string[];
  call_count: number;
  avg_latency: number;
  error_rate: number;
}

interface SpanTreeNode {
  span_id: string;
  parent_id: string | null;
  service: string;
  operation: string;
  start_time: string;
  duration_ms: number;
  self_duration_ms: number;
  status: string;
  depth: number;
  children: SpanTreeNode[];
  tags: Record<string, any>;
}

interface AdvancedFilter {
  minDuration?: number;
  maxDuration?: number;
  status?: string;
  startTime?: string;
  endTime?: string;
  hasErrors?: boolean;
  serviceFilter?: string[];
  operationFilter?: string[];
}

// ============================================================
// Tab Types
// ============================================================

type TabType = 'traces' | 'spans' | 'services' | 'operations' | 'analytics' | 'performance' | 'dependencies' | 'flamegraph';

// ============================================================
// Main Component
// ============================================================

export default function TracingPage() {
  const [activeTab, setActiveTab] = useState<TabType>('traces');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [selectedOperation, setSelectedOperation] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState('1h');
  const [granularity, setGranularity] = useState('1m');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [advancedFilters, setAdvancedFilters] = useState<AdvancedFilter>({});
  const [expandedSpans, setExpandedSpans] = useState<Set<string>>(new Set());
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);

  const queryClient = useQueryClient();
  const toast = useToast();
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);

  // ============================================================
  // API Configuration
  // ============================================================

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api';

  // ============================================================
  // Query Hooks
  // ============================================================

  // Fetch traces list
  const { data: tracesData, isLoading: tracesLoading, error: tracesError, refetch: refetchTraces } = useQuery({
    queryKey: ['tracing-traces', searchQuery, selectedService, advancedFilters],
    queryFn: async () => {
      // Use search endpoint when advanced filters are present
      if (showAdvancedFilters && (advancedFilters.minDuration || advancedFilters.maxDuration || advancedFilters.status || advancedFilters.hasErrors)) {
        const searchBody = {
          query: searchQuery || '',
          service_name: selectedService || undefined,
          min_duration: advancedFilters.minDuration,
          max_duration: advancedFilters.maxDuration,
          status: advancedFilters.status,
          limit: 50,
        };

        const resp = await api.post(`${API_BASE}/v1/tracing/search`, searchBody);
        return resp.data;
      }

      // Use standard list endpoint for simple queries
      const params = new URLSearchParams();
      params.append('limit', '50');
      if (selectedService) params.append('service_name', selectedService);
      if (searchQuery) params.append('query', searchQuery);

      const resp = await api.get(`${API_BASE}/v1/tracing/traces?${params.toString()}`);
      return resp.data;
    },
    refetchInterval: 15000,
  });

  // Fetch trace detail
  const { data: traceDetailData, isLoading: detailLoading, refetch: refetchDetail } = useQuery({
    queryKey: ['tracing-detail', selectedTrace?.trace_id],
    queryFn: async () => {
      const resp = await api.get(`${API_BASE}/v1/tracing/traces/${selectedTrace?.trace_id}`);
      return resp.data;
    },
    enabled: !!selectedTrace,
  });

  // Fetch spans
  const { data: spansData, isLoading: spansLoading, refetch: refetchSpans } = useQuery({
    queryKey: ['tracing-spans', selectedTrace?.trace_id, selectedService],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('limit', '100');
      if (selectedTrace?.trace_id) params.append('trace_id', selectedTrace.trace_id);
      if (selectedService) params.append('service', selectedService);

      const resp = await api.get(`${API_BASE}/v1/tracing/spans?${params.toString()}`);
      return resp.data;
    },
    enabled: activeTab === 'spans',
  });

  // Fetch services
  const { data: servicesData, isLoading: servicesLoading, refetch: refetchServices } = useQuery({
    queryKey: ['tracing-services'],
    queryFn: async () => {
      const resp = await api.get(`${API_BASE}/v1/tracing/services`);
      return resp.data;
    },
    enabled: activeTab === 'services',
  });

  // Fetch operations
  const { data: operationsData, isLoading: operationsLoading, refetch: refetchOperations } = useQuery({
    queryKey: ['tracing-operations', selectedService],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedService) params.append('service', selectedService);

      const resp = await api.get(`${API_BASE}/v1/tracing/operations?${params.toString()}`);
      return resp.data;
    },
    enabled: activeTab === 'operations',
  });

  // Fetch analytics
  const { data: analyticsData, isLoading: analyticsLoading, refetch: refetchAnalytics } = useQuery({
    queryKey: ['tracing-analytics', selectedService, selectedOperation],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('limit', '100');
      if (selectedService) params.append('service', selectedService);
      if (selectedOperation) params.append('operation', selectedOperation);

      const resp = await api.get(`${API_BASE}/v1/tracing/analytics?${params.toString()}`);
      return resp.data;
    },
    enabled: activeTab === 'analytics',
  });

  // Fetch performance metrics
  const { data: performanceData, isLoading: performanceLoading, refetch: refetchPerformance } = useQuery({
    queryKey: ['tracing-performance', selectedService, selectedOperation, timeRange, granularity],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('time_range', timeRange);
      params.append('granularity', granularity);
      if (selectedService) params.append('service', selectedService);
      if (selectedOperation) params.append('operation', selectedOperation);

      const resp = await api.get(`${API_BASE}/v1/tracing/performance?${params.toString()}`);
      return resp.data;
    },
    enabled: activeTab === 'performance',
  });

  // Fetch service dependencies
  const { data: dependenciesData, isLoading: dependenciesLoading, refetch: refetchDependencies } = useQuery({
    queryKey: ['tracing-dependencies', selectedService],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedService) params.append('service', selectedService);

      const resp = await api.get(`${API_BASE}/v1/tracing/dependencies?${params.toString()}`);
      return resp.data;
    },
    enabled: activeTab === 'dependencies',
  });

  // Fetch flame graph data
  const { data: flameGraphData, isLoading: flameGraphLoading, refetch: refetchFlameGraph } = useQuery({
    queryKey: ['tracing-flamegraph', selectedTrace?.trace_id],
    queryFn: async () => {
      if (!selectedTrace?.trace_id) return null;

      const resp = await api.get(`${API_BASE}/v1/tracing/traces/${selectedTrace.trace_id}/flamegraph`);
      return resp.data;
    },
    enabled: activeTab === 'flamegraph' && !!selectedTrace?.trace_id,
  });

  // ============================================================
  // Mutation Hooks
  // ============================================================

  // Create trace mutation
  const createTraceMutation = useMutation({
    mutationFn: async (traceData: Partial<Trace>) => {
      const resp = await api.post(`${API_BASE}/v1/tracing/traces`, {
        trace_id: traceData.trace_id || `trace-${Date.now()}`,
        root_service: traceData.root_service || 'unknown',
        operation: traceData.operation || 'unknown',
        duration_ms: traceData.duration_ms || 0,
        status: traceData.status || 'ok',
        tags: traceData.tags || {},
      });
      return resp.data;
    },
    onSuccess: () => {
      toast.success('Trace created successfully');
      queryClient.invalidateQueries({ queryKey: ['tracing-traces'] });
    },
    onError: (error: any) => {
      toast.error(`Failed to create trace: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete trace mutation
  const deleteTraceMutation = useMutation({
    mutationFn: async (traceId: string) => {
      const resp = await api.delete(`${API_BASE}/v1/tracing/traces/${traceId}`);
      return resp.data;
    },
    onSuccess: () => {
      toast.success('Trace deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['tracing-traces'] });
      setSelectedTrace(null);
    },
    onError: (error: any) => {
      toast.error(`Failed to delete trace: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Create span mutation
  const createSpanMutation = useMutation({
    mutationFn: async (spanData: Partial<Span>) => {
      const resp = await api.post(`${API_BASE}/v1/tracing/spans`, {
        span_id: spanData.span_id || `span-${Date.now()}`,
        trace_id: spanData.trace_id || selectedTrace?.trace_id || '',
        parent_id: spanData.parent_id || null,
        service: spanData.service || 'unknown',
        operation: spanData.operation || 'unknown',
        start_time: spanData.start_time || new Date().toISOString(),
        duration_ms: spanData.duration_ms || 0,
        status: spanData.status || 'ok',
        tags: spanData.tags || {},
      });
      return resp.data;
    },
    onSuccess: () => {
      toast.success('Span created successfully');
      queryClient.invalidateQueries({ queryKey: ['tracing-spans'] });
    },
    onError: (error: any) => {
      toast.error(`Failed to create span: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete span mutation
  const deleteSpanMutation = useMutation({
    mutationFn: async (spanId: string) => {
      const resp = await api.delete(`${API_BASE}/v1/tracing/spans/${spanId}`);
      return resp.data;
    },
    onSuccess: () => {
      toast.success('Span deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['tracing-spans'] });
    },
    onError: (error: any) => {
      toast.error(`Failed to delete span: ${error.response?.data?.detail || error.message}`);
    },
  });

  // ============================================================
  // Error Handling
  // ============================================================

  useEffect(() => {
    if (tracesError) {
      toast.error('Failed to load tracing data');
      setPageError(tracesError as Error);
    }
  }, [tracesError, toast, setPageError]);

  // ============================================================
  // Data Extraction
  // ============================================================

  const traces = tracesData?.items || [];
  const traceDetail = traceDetailData || null;
  const spans = spansData?.items || [];
  const services = servicesData?.items || [];
  const operations = operationsData?.items || [];
  const analytics = analyticsData?.items || [];
  const performance = performanceData as PerformanceMetrics | null;
  const dependencies = dependenciesData?.items || [];
  const flameGraph = flameGraphData as SpanTreeNode | null;

  // ============================================================
  // Helper Functions for Advanced Features
  // ============================================================

  const buildSpanTree = useCallback((spans: Span[]): SpanTreeNode[] => {
    const spanMap = new Map<string, SpanTreeNode>();
    const rootSpans: SpanTreeNode[] = [];

    // First pass: create all nodes
    spans.forEach(span => {
      const node: SpanTreeNode = {
        span_id: span.span_id,
        parent_id: span.parent_id,
        service: span.service,
        operation: span.operation,
        start_time: span.start_time,
        duration_ms: span.duration_ms,
        self_duration_ms: span.duration_ms, // Will be calculated
        status: span.status,
        depth: 0,
        children: [],
        tags: span.tags,
      };
      spanMap.set(span.span_id, node);
    });

    // Second pass: build tree structure and calculate self duration
    spans.forEach(span => {
      const node = spanMap.get(span.span_id);
      if (!node) return;

      if (span.parent_id && spanMap.has(span.parent_id)) {
        const parent = spanMap.get(span.parent_id)!;
        parent.children.push(node);
        node.depth = parent.depth + 1;
        // Subtract child duration from parent self duration
        parent.self_duration_ms -= span.duration_ms;
      } else {
        rootSpans.push(node);
      }
    });

    return rootSpans;
  }, []);

  const toggleSpanExpansion = useCallback((spanId: string) => {
    setExpandedSpans(prev => {
      const newSet = new Set(prev);
      if (newSet.has(spanId)) {
        newSet.delete(spanId);
      } else {
        newSet.add(spanId);
      }
      return newSet;
    });
  }, []);

  const handleSort = useCallback((key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev?.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  }, []);

  const sortedTraces = useMemo(() => {
    if (!sortConfig) return traces;

    return [...traces].sort((a, b) => {
      const aValue = a[sortConfig.key as keyof Trace];
      const bValue = b[sortConfig.key as keyof Trace];

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortConfig.direction === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      return 0;
    });
  }, [traces, sortConfig]);

  const handleExportData = useCallback(async (format: 'json' | 'csv') => {
    try {
      const dataToExport = activeTab === 'traces' ? traces :
        activeTab === 'spans' ? spans :
          activeTab === 'services' ? services :
            activeTab === 'operations' ? operations :
              activeTab === 'analytics' ? analytics : [];

      if (format === 'json') {
        const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `tracing-${activeTab}-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
      } else if (format === 'csv') {
        if (dataToExport.length === 0) {
          toast.error('No data to export');
          return;
        }

        const headers = Object.keys(dataToExport[0]);
        const csvContent = [
          headers.join(','),
          ...dataToExport.map(row => headers.map(header => {
            const value = row[header];
            const stringValue = typeof value === 'object' ? JSON.stringify(value) : String(value);
            return `"${stringValue.replace(/"/g, '""')}"`;
          }).join(',')),
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `tracing-${activeTab}-${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }

      toast.success(`Data exported as ${format.toUpperCase()}`);
    } catch (error) {
      toast.error(`Failed to export data: ${error}`);
    }
  }, [activeTab, traces, spans, services, operations, analytics, toast]);

  const handleClearFilters = useCallback(() => {
    setAdvancedFilters({});
    setShowAdvancedFilters(false);
    setSearchQuery('');
    setSelectedService(null);
    setSelectedOperation(null);
  }, []);

  // ============================================================
  // Column Definitions
  // ============================================================

  const traceColumns = [
    { key: 'trace_id' as const, label: '追踪ID' },
    { key: 'root_service' as const, label: '服务' },
    { key: 'operation' as const, label: '操作' },
    { key: 'duration_ms' as const, label: '持续时间', render: (value: number) => `${value.toFixed(2)}ms` },
    {
      key: 'status' as const, label: '状态', render: (value: string) => (
        <StatusBadge status={value === 'ok' ? 'success' : value === 'error' ? 'error' : 'warning'} text={value} />
      )
    },
    { key: 'start_time' as const, label: '时间', render: (value: string) => new Date(value).toLocaleString() },
  ];

  const spanColumns = [
    { key: 'span_id' as const, label: 'Span ID' },
    { key: 'trace_id' as const, label: '追踪ID' },
    { key: 'service' as const, label: '服务' },
    { key: 'operation' as const, label: '操作' },
    { key: 'duration_ms' as const, label: '持续时间', render: (value: number) => `${value.toFixed(2)}ms` },
    {
      key: 'status' as const, label: '状态', render: (value: string) => (
        <StatusBadge status={value === 'ok' ? 'success' : 'error'} text={value} />
      )
    },
  ];

  const serviceColumns = [
    { key: 'name' as const, label: '服务名称' },
    { key: 'type' as const, label: '类型' },
    { key: 'version' as const, label: '版本' },
  ];

  const operationColumns = [
    { key: 'id' as const, label: '操作ID' },
    { key: 'name' as const, label: '操作名称' },
    { key: 'service' as const, label: '服务' },
    { key: 'type' as const, label: '类型' },
  ];

  const analyticsColumns = [
    { key: 'id' as const, label: 'ID' },
    { key: 'service' as const, label: '服务' },
    { key: 'operation' as const, label: '操作' },
    { key: 'metric_type' as const, label: '指标类型' },
    { key: 'value' as const, label: '值' },
    { key: 'timestamp' as const, label: '时间', render: (value: string) => new Date(value).toLocaleString() },
  ];

  // ============================================================
  // Event Handlers
  // ============================================================

  const handleTraceClick = (trace: Trace) => {
    setSelectedTrace(trace);
    setShowDetailModal(true);
  };

  const handleCreateTrace = () => {
    createTraceMutation.mutate({
      root_service: 'demo-service',
      operation: '/api/demo',
      duration_ms: Math.random() * 1000,
      status: 'ok',
    });
  };

  const handleDeleteTrace = (traceId: string) => {
    if (confirm('Are you sure you want to delete this trace?')) {
      deleteTraceMutation.mutate(traceId);
    }
  };

  const handleCreateSpan = () => {
    if (!selectedTrace?.trace_id) {
      toast.error('Please select a trace first');
      return;
    }
    createSpanMutation.mutate({
      trace_id: selectedTrace.trace_id,
      service: 'demo-service',
      operation: '/api/demo/span',
      duration_ms: Math.random() * 500,
      status: 'ok',
    });
  };

  const handleDeleteSpan = (spanId: string) => {
    if (confirm('Are you sure you want to delete this span?')) {
      deleteSpanMutation.mutate(spanId);
    }
  };

  // ============================================================
  // KPI Calculations
  // ============================================================

  const avgDuration = traces.length > 0 ? traces.reduce((sum, t) => sum + (t.duration_ms || 0), 0) / traces.length : 0;
  const errorRate = traces.length > 0 ? (traces.filter((t) => t.status === 'error').length / traces.length) * 100 : 0;
  const totalTraces = traces.length;
  const totalSpans = spans.length;
  const totalServices = services.length;
  const totalOperations = operations.length;

  // ============================================================
  // Loading State
  // ============================================================

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
          action={<Button onClick={() => refetchTraces()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchTraces()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  // ============================================================
  // Render
  // ============================================================

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">链路追踪</h1>
            <p className="text-sm text-gray-500">分布式链路追踪和性能分析</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchTraces()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4" />
              总追踪数
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{totalTraces}</p>
            <p className="text-sm text-gray-500 mt-1">总追踪记录</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="h-4 w-4" />
              平均持续时间
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{avgDuration.toFixed(2)}ms</p>
            <p className="text-sm text-gray-500 mt-1">平均响应时间</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              错误率
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${errorRate > 5 ? 'text-red-600' : 'text-green-600'}`}>
              {errorRate.toFixed(1)}%
            </p>
            <p className="text-sm text-gray-500 mt-1">错误追踪占比</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Layers className="h-4 w-4" />
              总Span数
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">{totalSpans}</p>
            <p className="text-sm text-gray-500 mt-1">总Span记录</p>
          </CardContent>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'traces' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('traces')}
          className="flex items-center gap-2"
        >
          <Activity className="h-4 w-4" />
          追踪管理
        </Button>
        <Button
          variant={activeTab === 'spans' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('spans')}
          className="flex items-center gap-2"
        >
          <Layers className="h-4 w-4" />
          Span分析
        </Button>
        <Button
          variant={activeTab === 'services' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('services')}
          className="flex items-center gap-2"
        >
          <Network className="h-4 w-4" />
          服务依赖
        </Button>
        <Button
          variant={activeTab === 'operations' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('operations')}
          className="flex items-center gap-2"
        >
          <Zap className="h-4 w-4" />
          操作管理
        </Button>
        <Button
          variant={activeTab === 'analytics' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('analytics')}
          className="flex items-center gap-2"
        >
          <Database className="h-4 w-4" />
          分析数据
        </Button>
        <Button
          variant={activeTab === 'performance' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('performance')}
          className="flex items-center gap-2"
        >
          <BarChart3 className="h-4 w-4" />
          性能分析
        </Button>
        <Button
          variant={activeTab === 'dependencies' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('dependencies')}
          className="flex items-center gap-2"
        >
          <GitBranch className="h-4 w-4" />
          服务依赖
        </Button>
        <Button
          variant={activeTab === 'flamegraph' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('flamegraph')}
          className="flex items-center gap-2"
          disabled={!selectedTrace}
        >
          <Flame className="h-4 w-4" />
          火焰图
        </Button>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索追踪ID、服务或操作"
                className="pl-10"
              />
            </div>
            <select
              value={selectedService || ''}
              onChange={(e) => setSelectedService(e.target.value || null)}
              className="px-3 py-2 border rounded-md"
            >
              <option value="">所有服务</option>
              {services.map((s: Service) => (
                <option key={s.name} value={s.name}>{s.name}</option>
              ))}
            </select>
            <select
              value={selectedOperation || ''}
              onChange={(e) => setSelectedOperation(e.target.value || null)}
              className="px-3 py-2 border rounded-md"
            >
              <option value="">所有操作</option>
              {operations.map((o: Operation) => (
                <option key={o.id} value={o.name}>{o.name}</option>
              ))}
            </select>
            <Button
              variant="outline"
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className="flex items-center gap-2"
            >
              <Filter className="h-4 w-4" />
              高级筛选
            </Button>
            {(searchQuery || selectedService || selectedOperation || showAdvancedFilters) && (
              <Button
                variant="ghost"
                onClick={handleClearFilters}
                className="flex items-center gap-2"
              >
                <X className="h-4 w-4" />
                清除筛选
              </Button>
            )}
          </div>

          {showAdvancedFilters && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">最小持续时间 (ms)</label>
                  <Input
                    type="number"
                    value={advancedFilters.minDuration || ''}
                    onChange={(e) => setAdvancedFilters(prev => ({ ...prev, minDuration: e.target.value ? Number(e.target.value) : undefined }))}
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">最大持续时间 (ms)</label>
                  <Input
                    type="number"
                    value={advancedFilters.maxDuration || ''}
                    onChange={(e) => setAdvancedFilters(prev => ({ ...prev, maxDuration: e.target.value ? Number(e.target.value) : undefined }))}
                    placeholder="∞"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <select
                    value={advancedFilters.status || ''}
                    onChange={(e) => setAdvancedFilters(prev => ({ ...prev, status: e.target.value || undefined }))}
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="">全部</option>
                    <option value="ok">成功</option>
                    <option value="error">错误</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="hasErrors"
                  checked={advancedFilters.hasErrors || false}
                  onChange={(e) => setAdvancedFilters(prev => ({ ...prev, hasErrors: e.target.checked || undefined }))}
                  className="rounded"
                />
                <label htmlFor="hasErrors" className="text-sm text-gray-700">仅显示包含错误的追踪</label>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tab Content */}
      {activeTab === 'traces' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                追踪列表 ({traces.length})
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreateTrace} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  创建追踪
                </Button>
                <Button onClick={() => handleExportData('json')} size="sm" variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  导出JSON
                </Button>
                <Button onClick={() => handleExportData('csv')} size="sm" variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  导出CSV
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {tracesLoading ? (
              <LoadingSpinner />
            ) : sortedTraces.length === 0 ? (
              <EmptyState
                title="暂无追踪数据"
                description="当前没有可用的链路追踪数据"
              />
            ) : (
              <DataTable
                data={sortedTraces}
                columns={traceColumns}
                pageSize={15}
                emptyMessage="暂无追踪数据"
                onRowClick={handleTraceClick}
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'spans' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="h-5 w-5" />
                Span列表 ({spans.length})
              </div>
              <Button onClick={handleCreateSpan} size="sm">
                <Plus className="h-4 w-4 mr-2" />
                创建Span
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {spansLoading ? (
              <LoadingSpinner />
            ) : spans.length === 0 ? (
              <EmptyState
                title="暂无Span数据"
                description="当前没有可用的Span数据"
              />
            ) : (
              <DataTable
                data={spans}
                columns={spanColumns}
                pageSize={15}
                emptyMessage="暂无Span数据"
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'services' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              服务列表 ({services.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {servicesLoading ? (
              <LoadingSpinner />
            ) : services.length === 0 ? (
              <EmptyState
                title="暂无服务数据"
                description="当前没有可用的服务数据"
              />
            ) : (
              <DataTable
                data={services}
                columns={serviceColumns}
                pageSize={15}
                emptyMessage="暂无服务数据"
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'operations' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              操作列表 ({operations.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {operationsLoading ? (
              <LoadingSpinner />
            ) : operations.length === 0 ? (
              <EmptyState
                title="暂无操作数据"
                description="当前没有可用的操作数据"
              />
            ) : (
              <DataTable
                data={operations}
                columns={operationColumns}
                pageSize={15}
                emptyMessage="暂无操作数据"
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'analytics' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              分析数据 ({analytics.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {analyticsLoading ? (
              <LoadingSpinner />
            ) : analytics.length === 0 ? (
              <EmptyState
                title="暂无分析数据"
                description="当前没有可用的分析数据"
              />
            ) : (
              <DataTable
                data={analytics}
                columns={analyticsColumns}
                pageSize={15}
                emptyMessage="暂无分析数据"
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'performance' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                性能指标
              </div>
              <div className="flex gap-2">
                <select
                  value={timeRange}
                  onChange={(e) => setTimeRange(e.target.value)}
                  className="px-3 py-2 border rounded-md text-sm"
                >
                  <option value="1h">1小时</option>
                  <option value="6h">6小时</option>
                  <option value="24h">24小时</option>
                  <option value="7d">7天</option>
                </select>
                <select
                  value={granularity}
                  onChange={(e) => setGranularity(e.target.value)}
                  className="px-3 py-2 border rounded-md text-sm"
                >
                  <option value="1m">1分钟</option>
                  <option value="5m">5分钟</option>
                  <option value="15m">15分钟</option>
                  <option value="1h">1小时</option>
                </select>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {performanceLoading ? (
              <LoadingSpinner />
            ) : performance ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <p className="text-sm text-gray-600">平均延迟</p>
                    <p className="text-2xl font-bold text-blue-600">{performance.metrics.avg_duration_ms.toFixed(2)}ms</p>
                  </div>
                  <div className="p-4 bg-green-50 rounded-lg">
                    <p className="text-sm text-gray-600">P50延迟</p>
                    <p className="text-2xl font-bold text-green-600">{performance.metrics.p50_duration_ms.toFixed(2)}ms</p>
                  </div>
                  <div className="p-4 bg-yellow-50 rounded-lg">
                    <p className="text-sm text-gray-600">P95延迟</p>
                    <p className="text-2xl font-bold text-yellow-600">{performance.metrics.p95_duration_ms.toFixed(2)}ms</p>
                  </div>
                  <div className="p-4 bg-red-50 rounded-lg">
                    <p className="text-sm text-gray-600">P99延迟</p>
                    <p className="text-2xl font-bold text-red-600">{performance.metrics.p99_duration_ms.toFixed(2)}ms</p>
                  </div>
                  <div className="p-4 bg-purple-50 rounded-lg">
                    <p className="text-sm text-gray-600">错误率</p>
                    <p className="text-2xl font-bold text-purple-600">{(performance.metrics.error_rate * 100).toFixed(2)}%</p>
                  </div>
                  <div className="p-4 bg-indigo-50 rounded-lg">
                    <p className="text-sm text-gray-600">吞吐量</p>
                    <p className="text-2xl font-bold text-indigo-600">{performance.metrics.throughput_per_hour.toFixed(2)}/h</p>
                  </div>
                  <div className="p-4 bg-pink-50 rounded-lg">
                    <p className="text-sm text-gray-600">总追踪数</p>
                    <p className="text-2xl font-bold text-pink-600">{performance.total_traces}</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">错误数</p>
                    <p className="text-2xl font-bold text-gray-600">{performance.metrics.error_count}</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-4">时间序列数据</h3>
                  <div className="h-64 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>
                          <th className="px-4 py-2 text-left">时间</th>
                          <th className="px-4 py-2 text-left">平均延迟</th>
                          <th className="px-4 py-2 text-left">错误率</th>
                          <th className="px-4 py-2 text-left">吞吐量</th>
                        </tr>
                      </thead>
                      <tbody>
                        {performance.time_series.map((item, index) => (
                          <tr key={index} className="border-b">
                            <td className="px-4 py-2">{new Date(item.timestamp).toLocaleString()}</td>
                            <td className="px-4 py-2">{item.avg_duration.toFixed(2)}ms</td>
                            <td className="px-4 py-2">{(item.error_rate * 100).toFixed(2)}%</td>
                            <td className="px-4 py-2">{item.throughput.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : (
              <EmptyState
                title="暂无性能数据"
                description="当前没有可用的性能数据"
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'dependencies' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitBranch className="h-5 w-5" />
                服务依赖图 ({dependencies.length})
              </div>
              <Button onClick={() => handleExportData('json')} size="sm" variant="outline">
                <Download className="h-4 w-4 mr-2" />
                导出
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {dependenciesLoading ? (
              <LoadingSpinner />
            ) : dependencies.length === 0 ? (
              <EmptyState
                title="暂无依赖数据"
                description="当前没有可用的服务依赖数据"
              />
            ) : (
              <div className="space-y-4">
                {dependencies.map((dep: ServiceDependency, index: number) => (
                  <div key={index} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-lg">{dep.service}</h3>
                      <div className="flex gap-2 text-sm">
                        <span className="px-2 py-1 bg-blue-100 rounded">调用: {dep.call_count}</span>
                        <span className="px-2 py-1 bg-green-100 rounded">延迟: {dep.avg_latency.toFixed(2)}ms</span>
                        <span className="px-2 py-1 bg-red-100 rounded">错误率: {(dep.error_rate * 100).toFixed(2)}%</span>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {dep.depends_on.map((depService, idx) => (
                        <div key={idx} className="flex items-center gap-1 text-sm">
                          <span className="px-2 py-1 bg-gray-100 rounded">{depService}</span>
                          {idx < dep.depends_on.length - 1 && <ArrowUpDown className="h-4 w-4 text-gray-400" />}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'flamegraph' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Flame className="h-5 w-5" />
              火焰图 - {selectedTrace?.trace_id}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!selectedTrace ? (
              <EmptyState
                title="未选择追踪"
                description="请先选择一个追踪以查看火焰图"
              />
            ) : flameGraphLoading ? (
              <LoadingSpinner />
            ) : flameGraph ? (
              <div className="space-y-4">
                <FlameGraphView node={flameGraph} expandedSpans={expandedSpans} onToggle={toggleSpanExpansion} />
              </div>
            ) : (
              <EmptyState
                title="暂无火焰图数据"
                description="无法生成火焰图"
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Trace Detail Modal */}
      {selectedTrace && showDetailModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="max-w-4xl w-full max-h-[90vh] overflow-y-auto m-4">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>追踪详情</CardTitle>
                <Button variant="ghost" onClick={() => setShowDetailModal(false)}>
                  关闭
                </Button>
              </div>
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
                    <h3 className="text-lg font-semibold mb-4">服务列表</h3>
                    <div className="flex flex-wrap gap-2">
                      {traceDetail.services.map((service) => (
                        <span key={service} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                          {service}
                        </span>
                      ))}
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

                  <div className="flex gap-2">
                    <Button
                      variant="destructive"
                      onClick={() => {
                        handleDeleteTrace(selectedTrace.trace_id);
                        setShowDetailModal(false);
                      }}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      删除追踪
                    </Button>
                  </div>
                </div>
              ) : (
                <EmptyState title="暂无详情数据" description="无法加载追踪详情" />
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Flame Graph View Component
// ============================================================

interface FlameGraphViewProps {
  node: SpanTreeNode;
  expandedSpans: Set<string>;
  onToggle: (spanId: string) => void;
  depth?: number;
}

function FlameGraphView({ node, expandedSpans, onToggle, depth = 0 }: FlameGraphViewProps) {
  const isExpanded = expandedSpans.has(node.span_id);
  const hasChildren = node.children.length > 0;
  const maxDuration = node.duration_ms; // This should be the root duration
  const widthPercent = (node.duration_ms / maxDuration) * 100;
  const selfWidthPercent = (node.self_duration_ms / maxDuration) * 100;

  return (
    <div className="space-y-1">
      <div
        className="flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-gray-100"
        style={{ marginLeft: `${depth * 20}px` }}
        onClick={() => hasChildren && onToggle(node.span_id)}
      >
        {hasChildren && (
          <span className="text-gray-400">
            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </span>
        )}
        <div
          className="flex-1 h-6 rounded"
          style={{
            width: `${widthPercent}%`,
            backgroundColor: node.status === 'error' ? '#ef4444' : '#3b82f6',
            opacity: 0.7,
          }}
        >
          <div className="flex items-center justify-between px-2 text-xs text-white">
            <span className="truncate">{node.operation}</span>
            <span>{node.duration_ms.toFixed(2)}ms</span>
          </div>
        </div>
        <span className="text-xs text-gray-600 w-24 text-right">{node.service}</span>
      </div>

      {isExpanded && hasChildren && (
        <div className="space-y-1">
          {node.children.map(child => (
            <FlameGraphView
              key={child.span_id}
              node={child}
              expandedSpans={expandedSpans}
              onToggle={onToggle}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}