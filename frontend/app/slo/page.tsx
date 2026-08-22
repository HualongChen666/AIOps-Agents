'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { KpiCard } from '@/components/ui/KpiCard';
import { DataTable } from '@/components/ui/DataTable';
import { GaugeChart } from '@/components/charts/GaugeChart';
import { Target, TrendingUp, AlertTriangle, Plus, RefreshCw, FileText, Trash2, Edit } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface SLO {
  id: string;
  name: string;
  service: string;
  metric: string;
  target: number;
  current: number;
  window: string;
  errorBudget: number;
  burnRate: number;
  status: string;
  aggregation?: string;
}

interface SLAReport {
  id: string;
  service: string;
  period: string;
  compliance: number;
  violations: number;
  generated_at: string;
}

export default function SLOPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [selectedSLO, setSelectedSLO] = useState<SLO | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    service: '',
    metric: '',
    target: 99.9,
    window: '30d',
    alert_threshold: 95,
    aggregation: 'good_ratio',
  });

  const queryClient = useQueryClient();

  // 🔧 获取SLO列表
  const { data: sloData, isLoading: sloLoading, error: sloError, refetch: refetchSLO } = useQuery<{ slos: SLO[] }>({
    queryKey: ['slo-list'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/slo/');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 获取SLA报告
  const { data: reportData, isLoading: reportLoading, refetch: refetchReports } = useQuery<{ reports: SLAReport[] }>({
    queryKey: ['slo-reports'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/slo/reports');
      return resp.data;
    },
    refetchInterval: 300000, // 5分钟刷新
  });

  // 🔧 创建SLO
  const createSLOMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/slo/', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slo-list'] });
      setShowCreateModal(false);
      showSuccess('SLO创建成功');
    },
    onError: () => {
      showError('SLO创建失败');
    },
  });

  // 🔧 删除SLO
  const deleteSLOMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/slo/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slo-list'] });
      showSuccess('SLO删除成功');
    },
    onError: () => {
      showError('SLO删除失败');
    },
  });

  // 🔧 生成SLA报告
  const generateReportMutation = useMutation({
    mutationFn: async (period: string) => {
      const resp = await api.post('/api/v1/slo/reports', null, { params: { period } });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slo-reports'] });
      setShowReportModal(false);
      showSuccess('SLA报告生成成功');
    },
    onError: () => {
      showError('SLA报告生成失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(sloLoading || reportLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (sloError) {
      showError('Failed to load SLO data');
      setPageError(sloError as Error);
    }
  }, [sloError, showError, setPageError]);

  const slos = sloData?.slos || [];
  const reports = reportData?.reports || [];

  const sloColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'service' as const, label: '服务' },
    { key: 'metric' as const, label: '指标' },
    { key: 'target' as const, label: '目标', render: (value: number) => `${value.toFixed(2)}%` },
    { key: 'current' as const, label: '当前', render: (value: number) => `${value.toFixed(2)}%` },
    { key: 'errorBudget' as const, label: '错误预算', render: (value: number) => `${value.toFixed(2)}%` },
    { key: 'status' as const, label: '状态' },
  ];

  const reportColumns = [
    { key: 'service' as const, label: '服务' },
    { key: 'period' as const, label: '周期' },
    { key: 'compliance' as const, label: '合规率', render: (value: number) => `${value.toFixed(2)}%` },
    { key: 'violations' as const, label: '违规次数' },
    { key: 'generated_at' as const, label: '生成时间', render: (value: string) => new Date(value).toLocaleString() },
  ];

  const handleCreateSLO = () => {
    createSLOMutation.mutate(formData);
  };

  const handleDeleteSLO = (id: string) => {
    if (confirm('确定要删除这个SLO吗？')) {
      deleteSLOMutation.mutate(id);
    }
  };

  const handleGenerateReport = (period: string) => {
    generateReportMutation.mutate(period);
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
          description="无法加载SLO数据，请稍后重试"
          action={<Button onClick={() => refetchSLO()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchSLO()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  const avgCompliance = slos.length > 0 ? slos.reduce((sum, slo) => sum + slo.current, 0) / slos.length : 0;
  const criticalSLOs = slos.filter((slo) => slo.status === 'critical').length;
  const totalBudget = slos.reduce((sum, slo) => sum + slo.errorBudget, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Target className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">SLO管理</h1>
            <p className="text-sm text-gray-500">服务级别目标管理和SLA合规监控</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchSLO()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowReportModal(true)} variant="outline">
            <FileText className="h-4 w-4 mr-2" />
            生成报告
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            创建SLO
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KpiCard
          title="平均合规率"
          value={avgCompliance.toFixed(2)}
          unit="%"
          icon={Target}
          level={avgCompliance < 95 ? 'critical' : avgCompliance < 99 ? 'warning' : 'normal'}
          description="所有SLO的平均合规率"
        />
        <KpiCard
          title="关键SLO"
          value={criticalSLOs}
          icon={AlertTriangle}
          level={criticalSLOs > 0 ? 'critical' : 'normal'}
          description="状态为critical的SLO数量"
        />
        <KpiCard
          title="总错误预算"
          value={totalBudget.toFixed(2)}
          unit="%"
          icon={TrendingUp}
          level={totalBudget < 50 ? 'critical' : totalBudget < 80 ? 'warning' : 'normal'}
          description="所有SLO的错误预算总和"
        />
      </div>

      {/* SLO List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            SLO列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {slos.length === 0 ? (
            <EmptyState
              title="暂无SLO"
              description="当前没有配置的SLO规则"
              action={<Button onClick={() => setShowCreateModal(true)}>创建第一个SLO</Button>}
            />
          ) : (
            <DataTable
              data={slos}
              columns={sloColumns}
              pageSize={10}
              emptyMessage="暂无SLO"
              onRowClick={(slo) => setSelectedSLO(slo)}
            />
          )}
        </CardContent>
      </Card>

      {/* SLO Detail Modal */}
      {selectedSLO && (
        <EnhancedModal
          open={!!selectedSLO}
          onOpenChange={(open) => !open && setSelectedSLO(null)}
          title={selectedSLO.name}
          size="lg"
        >
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700">服务</label>
                <p className="text-gray-900">{selectedSLO.service}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">指标</label>
                <p className="text-gray-900">{selectedSLO.metric}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">目标</label>
                <p className="text-gray-900">{selectedSLO.target.toFixed(2)}%</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">当前</label>
                <p className="text-gray-900">{selectedSLO.current.toFixed(2)}%</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">错误预算</label>
                <p className="text-gray-900">{selectedSLO.errorBudget.toFixed(2)}%</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">燃烧率</label>
                <p className="text-gray-900">{selectedSLO.burnRate.toFixed(2)}x</p>
              </div>
            </div>
            <GaugeChart
              value={selectedSLO.current}
              min={0}
              max={100}
              title="当前合规率"
              color={selectedSLO.status === 'critical' ? '#ef4444' : selectedSLO.status === 'warning' ? '#f59e0b' : '#10b981'}
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => handleDeleteSLO(selectedSLO.id)}>
                <Trash2 className="h-4 w-4 mr-2" />
                删除
              </Button>
            </div>
          </div>
        </EnhancedModal>
      )}

      {/* Create SLO Modal */}
      <EnhancedModal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        title="创建SLO"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="SLO名称"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">服务</label>
            <Input
              value={formData.service}
              onChange={(e) => setFormData({ ...formData, service: e.target.value })}
              placeholder="服务名称"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">指标</label>
            <Input
              value={formData.metric}
              onChange={(e) => setFormData({ ...formData, metric: e.target.value })}
              placeholder="指标名称"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">目标 (%)</label>
            <Input
              type="number"
              value={formData.target}
              onChange={(e) => setFormData({ ...formData, target: Number(e.target.value) })}
              placeholder="99.9"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">时间窗口</label>
            <select
              value={formData.window}
              onChange={(e) => setFormData({ ...formData, window: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="1h">1小时</option>
              <option value="24h">24小时</option>
              <option value="7d">7天</option>
              <option value="30d">30天</option>
              <option value="90d">90天</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">告警阈值 (%)</label>
            <Input
              type="number"
              value={formData.alert_threshold}
              onChange={(e) => setFormData({ ...formData, alert_threshold: Number(e.target.value) })}
              placeholder="95"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              取消
            </Button>
            <Button onClick={handleCreateSLO} disabled={createSLOMutation.isPending}>
              {createSLOMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </div>
      </EnhancedModal>

      {/* Generate Report Modal */}
      <EnhancedModal
        open={showReportModal}
        onOpenChange={setShowReportModal}
        title="生成SLA报告"
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">报告周期</label>
            <select
              value="30d"
              onChange={(e) => handleGenerateReport((e.target as HTMLSelectElement).value)}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="7d">7天</option>
              <option value="30d">30天</option>
              <option value="90d">90天</option>
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowReportModal(false)}>
              取消
            </Button>
            <Button onClick={() => handleGenerateReport('30d')} disabled={generateReportMutation.isPending}>
              {generateReportMutation.isPending ? '生成中...' : '生成'}
            </Button>
          </div>
        </div>
      </EnhancedModal>

      {/* SLA Reports */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            SLA报告
          </CardTitle>
        </CardHeader>
        <CardContent>
          {reports.length === 0 ? (
            <EmptyState
              title="暂无SLA报告"
              description="当前没有生成的SLA合规报告"
            />
          ) : (
            <DataTable
              data={reports}
              columns={reportColumns}
              pageSize={10}
              emptyMessage="暂无SLA报告"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}