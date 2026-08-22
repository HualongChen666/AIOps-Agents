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
import { TestTube, RefreshCw, Play, Plus, FileText, Settings, Clock, CheckCircle, XCircle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface TestSuite {
  suite_id: string;
  suite_name: string;
  test_type: string;
  test_count: number;
  coverage_target: number;
}

interface AutomationJob {
  job_id: string;
  job_name: string;
  job_type: string;
  trigger_type: string;
  status: string;
  last_run: string;
}

interface AutomationStatus {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
}

interface FrameworkStatus {
  total_suites: number;
  total_tests: number;
  average_coverage: number;
  passed_tests: number;
}

export default function TestManagementPage() {
  const [activeTab, setActiveTab] = useState<'suites' | 'jobs' | 'automation' | 'reports'>('suites');
  const [showSuiteModal, setShowSuiteModal] = useState(false);
  const [showJobModal, setShowJobModal] = useState(false);
  const [suiteData, setSuiteData] = useState({
    suite_id: '',
    suite_name: '',
    test_type: 'unit',
    description: '',
    coverage_target: 80.0,
  });
  const [jobData, setJobData] = useState({
    job_id: '',
    job_name: '',
    job_type: 'regression',
    trigger_type: 'manual',
  });

  const queryClient = useQueryClient();

  // 🔧 获取自动化状态
  const { data: automationStatusData, isLoading: automationStatusLoading, refetch: refetchAutomationStatus } = useQuery<{ data: AutomationStatus; timestamp: string }>({
    queryKey: ['test-automation-status'],
    queryFn: async () => {
      const resp = await api.get('/api/test-automation/status');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 获取框架状态
  const { data: frameworkStatusData, isLoading: frameworkStatusLoading, refetch: refetchFrameworkStatus } = useQuery<{ data: FrameworkStatus; timestamp: string }>({
    queryKey: ['test-framework-status'],
    queryFn: async () => {
      const resp = await api.get('/api/test-framework/status');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 获取测试套件
  const { data: suitesData, isLoading: suitesLoading, refetch: refetchSuites } = useQuery<{ data: { suites: TestSuite[]; count: number }; timestamp: string }>({
    queryKey: ['test-framework-suites'],
    queryFn: async () => {
      const resp = await api.get('/api/test-framework/suites');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 创建测试套件
  const createSuiteMutation = useMutation({
    mutationFn: async (data: typeof suiteData) => {
      const resp = await api.post('/api/test-framework/suite/create', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['test-framework-suites'] });
      queryClient.invalidateQueries({ queryKey: ['test-framework-status'] });
      setShowSuiteModal(false);
      showSuccess('测试套件创建成功');
    },
    onError: () => {
      showError('测试套件创建失败');
    },
  });

  // 🔧 创建自动化任务
  const createJobMutation = useMutation({
    mutationFn: async (data: typeof jobData) => {
      const resp = await api.post('/api/test-automation/job/create', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['test-automation-status'] });
      setShowJobModal(false);
      showSuccess('自动化任务创建成功');
    },
    onError: () => {
      showError('自动化任务创建失败');
    },
  });

  // 🔧 运行自动化任务
  const runJobMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const resp = await api.post(`/api/test-automation/job/${jobId}/run`);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['test-automation-status'] });
      showSuccess('任务已启动');
    },
    onError: () => {
      showError('任务启动失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(
    automationStatusLoading || frameworkStatusLoading || suitesLoading
  );

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (pageError) {
      showError('Failed to load test management data');
      setPageError(pageError as Error);
    }
  }, [pageError, showError, setPageError]);

  const automationStatus = automationStatusData?.data || { total_jobs: 0, active_jobs: 0, completed_jobs: 0, failed_jobs: 0 };
  const frameworkStatus = frameworkStatusData?.data || { total_suites: 0, total_tests: 0, average_coverage: 0, passed_tests: 0 };
  const suites = suitesData?.data?.suites || [];

  const handleCreateSuite = () => {
    createSuiteMutation.mutate(suiteData);
  };

  const handleCreateJob = () => {
    createJobMutation.mutate(jobData);
  };

  const handleRunJob = (jobId: string) => {
    runJobMutation.mutate(jobId);
  };

  const handleRefresh = () => {
    refetchAutomationStatus();
    refetchFrameworkStatus();
    refetchSuites();
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
          description="无法加载测试管理数据，请稍后重试"
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
          <TestTube className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">测试管理</h1>
            <p className="text-sm text-gray-500">测试套件和自动化任务管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowSuiteModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            创建套件
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总测试套件</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{frameworkStatus.total_suites}</p>
            <p className="text-sm text-gray-500 mt-1">测试套件总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总测试数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{frameworkStatus.total_tests}</p>
            <p className="text-sm text-gray-500 mt-1">测试用例总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均覆盖率</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">{frameworkStatus.average_coverage.toFixed(1)}%</p>
            <p className="text-sm text-gray-500 mt-1">代码覆盖率</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">自动化任务</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{automationStatus.total_jobs}</p>
            <p className="text-sm text-gray-500 mt-1">自动化任务总数</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'suites' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('suites')}
        >
          <FileText className="h-4 w-4 mr-2" />
          测试套件
        </Button>
        <Button
          variant={activeTab === 'jobs' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('jobs')}
        >
          <Clock className="h-4 w-4 mr-2" />
          自动化任务
        </Button>
        <Button
          variant={activeTab === 'automation' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('automation')}
        >
          <Settings className="h-4 w-4 mr-2" />
          自动化配置
        </Button>
        <Button
          variant={activeTab === 'reports' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('reports')}
        >
          <CheckCircle className="h-4 w-4 mr-2" />
          测试报告
        </Button>
      </div>

      {/* Suites Tab */}
      {activeTab === 'suites' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                测试套件
              </CardTitle>
              <Button size="sm" onClick={() => setShowSuiteModal(true)}>
                <Plus className="h-4 w-4 mr-1" />
                创建套件
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {suites.length > 0 ? (
              <div className="space-y-4">
                {suites.map((suite) => (
                  <div key={suite.suite_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h3 className="font-semibold text-lg">{suite.suite_name}</h3>
                        <p className="text-sm text-gray-500">{suite.test_type} - {suite.test_count} 个测试</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">覆盖率目标: {suite.coverage_target}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="暂无测试套件"
                description="测试框架暂无测试套件"
                action={<Button onClick={() => setShowSuiteModal(true)}>创建第一个套件</Button>}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Jobs Tab */}
      {activeTab === 'jobs' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                自动化任务
              </CardTitle>
              <Button size="sm" onClick={() => setShowJobModal(true)}>
                <Plus className="h-4 w-4 mr-1" />
                创建任务
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="自动化任务"
              description="管理和运行自动化测试任务"
              action={<Button onClick={() => setShowJobModal(true)}>创建第一个任务</Button>}
            />
          </CardContent>
        </Card>
      )}

      {/* Automation Tab */}
      {activeTab === 'automation' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              自动化配置
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="自动化配置"
              description="配置测试自动化和CI/CD流水线"
            />
          </CardContent>
        </Card>
      )}

      {/* Reports Tab */}
      {activeTab === 'reports' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              测试报告
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="测试报告"
              description="查看测试执行报告和覆盖率分析"
            />
          </CardContent>
        </Card>
      )}

      {/* Create Suite Modal */}
      <EnhancedModal
        open={showSuiteModal}
        onOpenChange={setShowSuiteModal}
        title="创建测试套件"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">套件ID</label>
            <input
              type="text"
              value={suiteData.suite_id}
              onChange={(e) => setSuiteData({ ...suiteData, suite_id: e.target.value })}
              placeholder="输入唯一套件ID"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">套件名称</label>
            <input
              type="text"
              value={suiteData.suite_name}
              onChange={(e) => setSuiteData({ ...suiteData, suite_name: e.target.value })}
              placeholder="输入套件名称"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">测试类型</label>
            <select
              value={suiteData.test_type}
              onChange={(e) => setSuiteData({ ...suiteData, test_type: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="unit">单元测试</option>
              <option value="integration">集成测试</option>
              <option value="end_to_end">端到端测试</option>
              <option value="performance">性能测试</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">覆盖率目标 (%)</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="100"
              value={String(suiteData.coverage_target)}
              onChange={(e) => setSuiteData({ ...suiteData, coverage_target: Number(e.target.value) })}
              placeholder="输入覆盖率目标 (0-100)"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea
              value={suiteData.description}
              onChange={(e) => setSuiteData({ ...suiteData, description: e.target.value })}
              placeholder="输入套件描述"
              className="w-full px-3 py-2 border rounded-md bg-white min-h-[100px]"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowSuiteModal(false)}>
              取消
            </Button>
            <Button onClick={handleCreateSuite} disabled={createSuiteMutation.isPending}>
              {createSuiteMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </div>
      </EnhancedModal>

      {/* Create Job Modal */}
      <EnhancedModal
        open={showJobModal}
        onOpenChange={setShowJobModal}
        title="创建自动化任务"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">任务ID</label>
            <input
              type="text"
              value={jobData.job_id}
              onChange={(e) => setJobData({ ...jobData, job_id: e.target.value })}
              placeholder="输入唯一任务ID"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">任务名称</label>
            <input
              type="text"
              value={jobData.job_name}
              onChange={(e) => setJobData({ ...jobData, job_name: e.target.value })}
              placeholder="输入任务名称"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">任务类型</label>
            <select
              value={jobData.job_type}
              onChange={(e) => setJobData({ ...jobData, job_type: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="regression">回归测试</option>
              <option value="smoke">冒烟测试</option>
              <option value="performance">性能测试</option>
              <option value="security">安全测试</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">触发类型</label>
            <select
              value={jobData.trigger_type}
              onChange={(e) => setJobData({ ...jobData, trigger_type: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="manual">手动触发</option>
              <option value="scheduled">定时触发</option>
              <option value="webhook">Webhook触发</option>
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowJobModal(false)}>
              取消
            </Button>
            <Button onClick={handleCreateJob} disabled={createJobMutation.isPending}>
              {createJobMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}