'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { KpiCard } from '@/components/ui/KpiCard';
import { GaugeChart } from '@/components/charts/GaugeChart';
import { TrendChart } from '@/components/charts/TrendChart';
import { TopologyGraph } from '@/components/TopologyGraph';
import { TrendingUp, RefreshCw, Search, AlertTriangle, Users, DollarSign, Activity, Download, BarChart3, Network, FileText } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface BusinessImpactService {
  id: string;
  name: string;
  category: string;
  impactScore: number;
  status: string;
  affectedUsers?: number;
  revenueImpact?: number;
  conversionRate?: number;
  conversionRateChange?: number;
  metrics?: {
    errorRate: number;
    responseTimeMs: number;
    cpuUsage: number;
    memoryUsage: number;
    pagerank: number;
  };
  impactFactors?: {
    priority: number;
    health: number;
  };
}

interface UXMetric {
  id: string;
  name: string;
  value: number;
  change: number;
  status: string;
}

interface BusinessImpactAssessment {
  name: string;
  impactScore: number;
  status: string;
  affectedUsers: number;
  revenueImpact: number;
  currentConversion: number;
  baselineConversion: number;
  conversionRateChange: number;
  metrics?: {
    errorRate: number;
    responseTimeMs: number;
    cpuUsage: number;
    memoryUsage: number;
    pagerank: number;
  };
  impactFactors?: {
    priority: number;
    health: number;
  };
}

interface TopologyData {
  nodes: Array<{
    id: string;
    label: string;
    status?: 'normal' | 'warning' | 'critical';
  }>;
  edges: Array<{
    source: string;
    target: string;
    label?: string;
  }>;
}

export default function BusinessImpactAdvancedPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [activeTab, setActiveTab] = useState<'overview' | 'trends' | 'topology' | 'report'>('overview');
  const [timeRange, setTimeRange] = useState('24h');

  // 🔧 获取业务影响服务列表
  const { data: servicesData, isLoading: servicesLoading, error: servicesError, refetch: refetchServices } = useQuery<{ status: string; data: BusinessImpactService[] }>({
    queryKey: ['business-impact-services'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/business-impact/services');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  // 🔧 获取用户体验指标
  const { data: uxMetricsData, isLoading: uxLoading, error: uxError, refetch: refetchUX } = useQuery<{ status: string; data: UXMetric[] }>({
    queryKey: ['business-impact-ux'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/business-impact/ux-metrics');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  // 🔧 获取业务影响评估
  const { data: assessmentData, isLoading: assessmentLoading, error: assessmentError, refetch: refetchAssessment } = useQuery<{ status: string; data: BusinessImpactAssessment }>({
    queryKey: ['business-impact-assessment', selectedService],
    queryFn: async () => {
      const resp = await api.get(`/api/v1/business-impact/assess/${selectedService}`);
      return resp.data;
    },
    enabled: !!selectedService,
    refetchInterval: 60000,
  });

  // 🔧 获取拓扑数据
  const { data: topologyData, isLoading: topologyLoading, error: topologyError } = useQuery<TopologyData>({
    queryKey: ['topology'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/topologies/full-link');
      return resp.data;
    },
    refetchInterval: 120000,
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(servicesLoading || uxLoading || assessmentLoading || topologyLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (servicesError) {
      showError('Failed to load business impact services');
      setPageError(servicesError as Error);
    }
    if (uxError) {
      showError('Failed to load UX metrics');
      setPageError(uxError as Error);
    }
    if (assessmentError) {
      showError('Failed to load business impact assessment');
      setPageError(assessmentError as Error);
    }
    if (topologyError) {
      showError('Failed to load topology data');
      setPageError(topologyError as Error);
    }
  }, [servicesError, uxError, assessmentError, topologyError, showError, setPageError]);

  const services = servicesData?.data || [];
  const uxMetrics = uxMetricsData?.data || [];
  const assessment = assessmentData?.data || null;

  const filteredServices = services.filter((service) => {
    if (searchQuery && !service.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !service.category.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (selectedCategory !== 'all' && service.category !== selectedCategory) {
      return false;
    }
    return true;
  });

  const categories = ['all', ...Array.from(new Set(services.map(s => s.category)))];

  const serviceColumns = [
    { key: 'name' as const, label: '服务名称' },
    { key: 'category' as const, label: '类别' },
    { key: 'impactScore' as const, label: '影响分数', render: (value: number) => value.toFixed(1) },
    {
      key: 'status' as const, label: '状态', render: (value: string) => (
        <StatusBadge status={value === 'healthy' ? 'success' : value === 'degraded' ? 'warning' : 'error'} text={value} />
      )
    },
    {
      key: 'affectedUsers' as const, label: '受影响用户', render: (value?: number) => 
        value ? value.toLocaleString() : '0'
    },
    {
      key: 'revenueImpact' as const, label: '收入影响', render: (value?: number) => 
        value ? `$${value.toLocaleString()}` : '$0'
    },
  ];

  const uxColumns = [
    { key: 'name' as const, label: '指标名称' },
    { key: 'value' as const, label: '当前值', render: (value: number) => value.toFixed(2) },
    {
      key: 'change' as const, label: '变化', render: (value: number) => (
        <span className={value < 0 ? 'text-green-600' : 'text-red-600'}>
          {value > 0 ? '+' : ''}{value.toFixed(1)}%
        </span>
      )
    },
    {
      key: 'status' as const, label: '状态', render: (value: string) => (
        <StatusBadge status={value === 'good' ? 'success' : value === 'warning' ? 'warning' : 'error'} text={value} />
      )
    },
  ];

  const handleServiceClick = (serviceName: string) => {
    setSelectedService(serviceName);
  };

  const handleRefresh = () => {
    refetchServices();
    refetchUX();
    if (selectedService) refetchAssessment();
  };

  const handleGenerateReport = () => {
    showSuccess('业务影响报告生成中...');
    // 实际实现中会调用报告生成API
  };

  const handleExportData = () => {
    const dataStr = JSON.stringify({ services, uxMetrics, assessment }, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `business-impact-report-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    showSuccess('数据导出成功');
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
          description="无法加载业务影响数据，请稍后重试"
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  const totalServices = services.length;
  const downServices = services.filter((s) => s.status === 'down').length;
  const degradedServices = services.filter((s) => s.status === 'degraded').length;
  const totalRevenueImpact = services.reduce((sum, s) => {
    if (s.revenueImpact) {
      return sum + s.revenueImpact;
    }
    return sum;
  }, 0);

  const tabs = [
    { key: 'overview' as const, label: '概览', icon: Activity },
    { key: 'trends' as const, label: '趋势分析', icon: TrendingUp },
    { key: 'topology' as const, label: '服务依赖', icon: Network },
    { key: 'report' as const, label: '报告', icon: FileText },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">高级业务影响分析</h1>
            <p className="text-sm text-gray-500">深度分析服务故障对业务的影响</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="w-32"
          >
            <option value="1h">1小时</option>
            <option value="6h">6小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
          </Select>
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={handleExportData} variant="outline">
            <Download className="h-4 w-4 mr-2" />
            导出
          </Button>
        </div>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${activeTab === tab.key
                  ? 'bg-[var(--accent-blue)] text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {activeTab === 'overview' && (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <KpiCard
              title="总服务数"
              value={totalServices}
              icon={Activity}
              level="normal"
              description="业务影响服务总数"
            />
            <KpiCard
              title="故障服务"
              value={downServices}
              icon={AlertTriangle}
              level={downServices > 0 ? 'critical' : 'normal'}
              description="当前故障的服务"
            />
            <KpiCard
              title="降级服务"
              value={degradedServices}
              icon={AlertTriangle}
              level={degradedServices > 0 ? 'warning' : 'normal'}
              description="当前降级的服务"
            />
            <KpiCard
              title="预估收入影响"
              value={totalRevenueImpact}
              unit="$"
              icon={DollarSign}
              level={totalRevenueImpact > 100000 ? 'critical' : totalRevenueImpact > 50000 ? 'warning' : 'normal'}
              description="故障导致的收入损失"
            />
          </div>

          {/* Search and Filter */}
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="搜索服务名称或类别"
                    className="pl-10"
                  />
                </div>
                <Select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                >
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat === 'all' ? '全部类别' : cat}
                    </option>
                  ))}
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Services List */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                业务影响服务 ({filteredServices.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {filteredServices.length === 0 ? (
                <EmptyState
                  title="暂无服务数据"
                  description="当前没有可用的业务影响服务"
                />
              ) : (
                <DataTable
                  data={filteredServices}
                  columns={serviceColumns}
                  pageSize={20}
                  emptyMessage="暂无服务数据"
                  onRowClick={(service) => handleServiceClick(service.name)}
                />
              )}
            </CardContent>
          </Card>

          {/* UX Metrics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                用户体验指标
              </CardTitle>
            </CardHeader>
            <CardContent>
              {uxMetrics.length === 0 ? (
                <EmptyState
                  title="暂无UX指标"
                  description="当前没有可用的用户体验指标"
                />
              ) : (
                <DataTable
                  data={uxMetrics}
                  columns={uxColumns}
                  pageSize={10}
                  emptyMessage="暂无UX指标"
                />
              )}
            </CardContent>
          </Card>

          {/* Business Impact Assessment */}
          {assessment && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  业务影响评估 - {assessment.name}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-700">影响分数</label>
                      <p className="text-2xl font-bold text-gray-900">{assessment.impactScore.toFixed(1)}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700">状态</label>
                      <p className="text-2xl font-bold text-gray-900">{assessment.status}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700">受影响用户</label>
                      <p className="text-2xl font-bold text-red-600">{assessment.affectedUsers.toLocaleString()}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700">收入影响</label>
                      <p className="text-2xl font-bold text-red-600">${assessment.revenueImpact.toLocaleString()}</p>
                    </div>
                  </div>

                  <GaugeChart
                    value={assessment.impactScore * 10}
                    min={0}
                    max={100}
                    title="业务影响分数"
                    color={assessment.impactScore > 7 ? '#ef4444' : assessment.impactScore > 4 ? '#f59e0b' : '#10b981'}
                  />

                  {/* 详细指标 */}
                  {assessment.metrics && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <label className="text-sm font-medium text-gray-700">错误率</label>
                        <p className="text-lg font-bold text-gray-900">{(assessment.metrics.errorRate * 100).toFixed(2)}%</p>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <label className="text-sm font-medium text-gray-700">响应时间</label>
                        <p className="text-lg font-bold text-gray-900">{assessment.metrics.responseTimeMs.toFixed(0)}ms</p>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <label className="text-sm font-medium text-gray-700">CPU使用率</label>
                        <p className="text-lg font-bold text-gray-900">{assessment.metrics.cpuUsage.toFixed(1)}%</p>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <label className="text-sm font-medium text-gray-700">内存使用率</label>
                        <p className="text-lg font-bold text-gray-900">{assessment.metrics.memoryUsage.toFixed(1)}%</p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {activeTab === 'trends' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                影响趋势分析
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <TrendChart
                  data={services.map(s => s.impactScore).slice(0, 10)}
                  labels={services.map(s => s.name).slice(0, 10)}
                  color="#3b82f6"
                  height={250}
                  title="服务影响分数趋势"
                />
                <TrendChart
                  data={uxMetrics.map(m => m.value).slice(0, 7)}
                  labels={uxMetrics.map(m => m.name).slice(0, 7)}
                  color="#10b981"
                  height={250}
                  title="用户体验指标趋势"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>收入影响趋势</CardTitle>
            </CardHeader>
            <CardContent>
              <TrendChart
                data={services.map(s => s.revenueImpact || 0).slice(0, 10)}
                labels={services.map(s => s.name).slice(0, 10)}
                color="#ef4444"
                height={300}
                title="各服务收入影响"
              />
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'topology' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              服务依赖关系
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topologyLoading ? (
              <LoadingSpinner size="lg" />
            ) : topologyError ? (
              <EmptyState
                title="拓扑加载失败"
                description="无法加载服务依赖关系"
              />
            ) : (
              <TopologyGraph onNodeClick={(nodeId) => handleServiceClick(nodeId)} />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'report' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                业务影响报告
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-6 bg-gray-50 rounded-lg">
                  <h3 className="text-lg font-semibold mb-4">报告摘要</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">总服务数</label>
                      <p className="text-2xl font-bold">{totalServices}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">故障服务</label>
                      <p className="text-2xl font-bold text-red-600">{downServices}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">降级服务</label>
                      <p className="text-2xl font-bold text-yellow-600">{degradedServices}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">总收入影响</label>
                      <p className="text-2xl font-bold text-red-600">${totalRevenueImpact.toLocaleString()}</p>
                    </div>
                  </div>
                </div>

                <div className="p-6 bg-gray-50 rounded-lg">
                  <h3 className="text-lg font-semibold mb-4">高风险服务</h3>
                  {services.filter(s => s.impactScore >= 7).slice(0, 5).map((service) => (
                    <div key={service.id} className="flex items-center justify-between py-2 border-b last:border-0">
                      <span className="font-medium">{service.name}</span>
                      <div className="flex items-center gap-4">
                        <StatusBadge 
                          status={service.status === 'healthy' ? 'success' : service.status === 'degraded' ? 'warning' : 'error'} 
                          text={service.status} 
                        />
                        <span className="font-bold">{service.impactScore.toFixed(1)}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-4">
                  <Button onClick={handleGenerateReport} className="flex-1">
                    <FileText className="h-4 w-4 mr-2" />
                    生成PDF报告
                  </Button>
                  <Button onClick={handleExportData} variant="outline" className="flex-1">
                    <Download className="h-4 w-4 mr-2" />
                    导出JSON数据
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
