'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { KpiCard } from '@/components/ui/KpiCard';
import { Target, RefreshCw, Plus, TrendingUp, AlertTriangle, CheckCircle, BarChart3 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface ModuleCoverage {
  module_id: string;
  module_name: string;
  total_lines: number;
  covered_lines: number;
  coverage_percentage: number;
  coverage_level: string;
  last_updated: string;
}

interface CoverageStatus {
  total_modules: number;
  average_coverage: number;
  excellent_modules: number;
  needs_improvement: number;
}

interface CoverageReport {
  modules: ModuleCoverage[];
  summary: CoverageStatus;
  trends: Array<{ date: string; coverage: number }>;
}

export default function TestCoveragePage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'modules' | 'trends' | 'thresholds'>('overview');
  const [showAddModal, setShowAddModal] = useState(false);
  const [moduleData, setModuleData] = useState({
    module_id: '',
    module_name: '',
    total_lines: 0,
    covered_lines: 0,
  });

  const queryClient = useQueryClient();

  // 🔧 获取覆盖率状态
  const { data: statusData, isLoading: statusLoading, refetch: refetchStatus } = useQuery<{ data: CoverageStatus; timestamp: string }>({
    queryKey: ['test-coverage-status'],
    queryFn: async () => {
      const resp = await api.get('/api/test-coverage/status');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 获取覆盖率报告
  const { data: reportData, isLoading: reportLoading, refetch: refetchReport } = useQuery<{ data: CoverageReport; timestamp: string }>({
    queryKey: ['test-coverage-report'],
    queryFn: async () => {
      const resp = await api.get('/api/test-coverage/report');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 添加模块覆盖率
  const addModuleMutation = useMutation({
    mutationFn: async (data: typeof moduleData) => {
      const resp = await api.post('/api/test-coverage/module/add', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['test-coverage-status'] });
      queryClient.invalidateQueries({ queryKey: ['test-coverage-report'] });
      setShowAddModal(false);
      showSuccess('模块覆盖率已添加');
    },
    onError: () => {
      showError('添加模块覆盖率失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(
    statusLoading || reportLoading
  );

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (pageError) {
      showError('Failed to load test coverage data');
      setPageError(pageError as Error);
    }
  }, [pageError, showError, setPageError]);

  const status = statusData?.data || { total_modules: 0, average_coverage: 0, excellent_modules: 0, needs_improvement: 0 };
  const report = reportData?.data || { modules: [], summary: status, trends: [] };

  const handleAddModule = () => {
    addModuleMutation.mutate(moduleData);
  };

  const handleRefresh = () => {
    refetchStatus();
    refetchReport();
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
          description="无法加载测试覆盖率数据，请稍后重试"
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Target className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">测试覆盖率</h1>
            <p className="text-sm text-gray-500">代码覆盖率分析和跟踪</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            添加模块
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总模块数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{status.total_modules}</p>
            <p className="text-sm text-gray-500 mt-1">已跟踪模块</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均覆盖率</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{status.average_coverage.toFixed(1)}%</p>
            <p className="text-sm text-gray-500 mt-1">整体覆盖率</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">优秀模块</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">{status.excellent_modules}</p>
            <p className="text-sm text-gray-500 mt-1">90%+ 覆盖率</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">需改进</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{status.needs_improvement}</p>
            <p className="text-sm text-gray-500 mt-1">&lt;70% 覆盖率</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'overview' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('overview')}
        >
          <Target className="h-4 w-4 mr-2" />
          概览
        </Button>
        <Button
          variant={activeTab === 'modules' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('modules')}
        >
          <BarChart3 className="h-4 w-4 mr-2" />
          模块详情
        </Button>
        <Button
          variant={activeTab === 'trends' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('trends')}
        >
          <TrendingUp className="h-4 w-4 mr-2" />
          趋势分析
        </Button>
        <Button
          variant={activeTab === 'thresholds' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('thresholds')}
        >
          <AlertTriangle className="h-4 w-4 mr-2" />
          阈值配置
        </Button>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              覆盖率概览
            </CardTitle>
          </CardHeader>
          <CardContent>
            {report.modules.length > 0 ? (
              <div className="space-y-4">
                {report.modules.slice(0, 5).map((module) => (
                  <div key={module.module_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h3 className="font-semibold text-lg">{module.module_name}</h3>
                        <p className="text-sm text-gray-500">{module.total_lines} 行代码</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={module.coverage_level as "error" | "success" | "warning" | "info" | "pending" | "unknown"} />
                        <span className="text-sm font-semibold">{module.coverage_percentage.toFixed(1)}%</span>
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${module.coverage_percentage >= 90
                          ? 'bg-green-500'
                          : module.coverage_percentage >= 80
                            ? 'bg-blue-500'
                            : module.coverage_percentage >= 70
                              ? 'bg-yellow-500'
                              : 'bg-red-500'
                          }`}
                        style={{ width: `${module.coverage_percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="暂无覆盖率数据"
                description="添加模块覆盖率以开始跟踪"
                action={<Button onClick={() => setShowAddModal(true)}>添加第一个模块</Button>}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Modules Tab */}
      {activeTab === 'modules' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              模块详情
            </CardTitle>
          </CardHeader>
          <CardContent>
            {report.modules.length > 0 ? (
              <div className="space-y-4">
                {report.modules.map((module) => (
                  <div key={module.module_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h3 className="font-semibold text-lg">{module.module_name}</h3>
                        <p className="text-sm text-gray-500">{module.module_id}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={module.coverage_level as "error" | "success" | "warning" | "info" | "pending" | "unknown"} />
                        <span className="text-sm font-semibold">{module.coverage_percentage.toFixed(1)}%</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">总行数: </span>
                        {module.total_lines}
                      </div>
                      <div>
                        <span className="text-gray-500">覆盖行数: </span>
                        {module.covered_lines}
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                      最后更新: {new Date(module.last_updated).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="暂无模块数据"
                description="添加模块覆盖率以查看详情"
                action={<Button onClick={() => setShowAddModal(true)}>添加模块</Button>}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Trends Tab */}
      {activeTab === 'trends' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              趋势分析
            </CardTitle>
          </CardHeader>
          <CardContent>
            {report.trends.length > 0 ? (
              <div className="h-64">
                <div className="text-center text-gray-500">
                  趋势图表将在数据积累后显示
                </div>
              </div>
            ) : (
              <EmptyState
                title="暂无趋势数据"
                description="覆盖率趋势将在数据积累后显示"
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Thresholds Tab */}
      {activeTab === 'thresholds' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              阈值配置
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="阈值配置"
              description="配置不同模块类型的覆盖率阈值"
            />
          </CardContent>
        </Card>
      )}

      {/* Add Module Modal */}
      <EnhancedModal
        open={showAddModal}
        onOpenChange={setShowAddModal}
        title="添加模块覆盖率"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">模块ID</label>
            <input
              type="text"
              value={moduleData.module_id}
              onChange={(e) => setModuleData({ ...moduleData, module_id: e.target.value })}
              placeholder="输入唯一模块ID"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">模块名称</label>
            <input
              type="text"
              value={moduleData.module_name}
              onChange={(e) => setModuleData({ ...moduleData, module_name: e.target.value })}
              placeholder="输入模块名称"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">总行数</label>
            <input
              type="number"
              value={String(moduleData.total_lines)}
              onChange={(e) => setModuleData({ ...moduleData, total_lines: Number(e.target.value) })}
              placeholder="输入代码总行数"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">覆盖行数</label>
            <input
              type="number"
              value={String(moduleData.covered_lines)}
              onChange={(e) => setModuleData({ ...moduleData, covered_lines: Number(e.target.value) })}
              placeholder="输入测试覆盖行数"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowAddModal(false)}>
              取消
            </Button>
            <Button onClick={handleAddModule} disabled={addModuleMutation.isPending}>
              {addModuleMutation.isPending ? '添加中...' : '添加'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}