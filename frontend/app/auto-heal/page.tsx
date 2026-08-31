'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Wrench, AlertTriangle, CheckCircle, XCircle, Clock, RefreshCw, Play, Pause, FileText, Settings, History, Shield, Code, TrendingUp, BarChart3, Activity } from 'lucide-react';

// ============================================================
// Type Definitions
// ============================================================

interface HealTask {
  id: string;
  alertId: string;
  alertTitle: string;
  healPlan: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'approved' | 'rejected' | 'executing' | 'completed' | 'failed';
  createdAt: string;
  approver?: string;
  approvalComment?: string;
  executionLog?: string;
  executionTime?: string;
}

interface HealStatistics {
  total_tasks: number;
  pending_tasks: number;
  approved_tasks: number;
  executing_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  success_rate: number;
  avg_execution_time: number;
}

interface RepairConfiguration {
  id: string;
  name: string;
  description: string;
  config_type: string;
  key: string;
  value: string;
  category: string;
  is_secret: boolean;
  is_active: boolean;
  updated_at: string;
  updated_by: string;
}

interface RepairScript {
  id: string;
  name: string;
  description: string;
  language: string;
  platform: string;
  category: string;
  content: string;
  status: string;
  created_at: string;
}

interface RepairHistoryItem {
  id: string;
  repair_type: string;
  target_resource: string;
  issue_description: string;
  status: string;
  start_time: string;
  end_time: string;
  duration: number | null;
  executed_by: string;
  details: string;
}

interface RiskAssessment {
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  factors: string[];
  recommendations: string[];
}

interface RepairEffectiveness {
  id: string;
  repair_id: string;
  repair_type: string;
  target_resource: string;
  success_rate: number;
  avg_repair_time: number;
  total_repairs: number;
  successful_repairs: number;
  failed_repairs: number;
  last_evaluated: string;
  trend: string;
}

// ============================================================
// Main Component
// ============================================================

export default function AutoHealPage() {
  const queryClient = useQueryClient();
  const [selectedTab, setSelectedTab] = useState<'pending' | 'approved' | 'executing' | 'completed' | 'failed'>('pending');
  const [selectedTask, setSelectedTask] = useState<HealTask | null>(null);
  const [approvalComment, setApprovalComment] = useState('');
  const [activeSection, setActiveSection] = useState<'tasks' | 'config' | 'history' | 'templates' | 'risk'>('tasks');
  const [selectedScript, setSelectedScript] = useState<RepairScript | null>(null);
  const [scriptFormOpen, setScriptFormOpen] = useState(false);
  const [configFormOpen, setConfigFormOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<RepairConfiguration | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRiskLevel, setFilterRiskLevel] = useState<string>('all');
  const [filterDateRange, setFilterDateRange] = useState<string>('all');
  const [historyDetailOpen, setHistoryDetailOpen] = useState(false);
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<RepairHistoryItem | null>(null);

  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // ============================================================
  // API Queries - Heal Tasks
  // ============================================================

  const { data: healTasks, isLoading: tasksLoading, error: tasksError, refetch: refetchTasks } = useQuery<HealTask[]>({
    queryKey: ['heal-tasks'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/approvals/pending');
      const items = resp.data?.items || [];
      return items.map((item: any) => ({
        id: item.alert_id || item.id || String(Date.now()),
        alertId: item.alert_id || item.id || '',
        alertTitle: item.title || item.alert_id || '修复方案',
        healPlan: item.proposal || item.heal_plan || item.description || '',
        riskLevel: (item.risk_level || 'low') as HealTask['riskLevel'],
        status: (item.status || 'pending') as HealTask['status'],
        createdAt: item.created_at || item.timestamp || new Date().toISOString(),
        approver: item.approver || '',
        approvalComment: item.approval_comment || '',
        executionLog: item.execution_log || '',
        executionTime: item.execution_time || '',
      }));
    },
    refetchInterval: 30000,
  });

  // ============================================================
  // API Queries - Heal Statistics
  // ============================================================

  const { data: healStats, isLoading: statsLoading, refetch: refetchStats } = useQuery<HealStatistics>({
    queryKey: ['heal-statistics'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/approvals/statistics');
      return resp.data || {
        total_tasks: 0,
        pending_tasks: 0,
        approved_tasks: 0,
        executing_tasks: 0,
        completed_tasks: 0,
        failed_tasks: 0,
        success_rate: 0,
        avg_execution_time: 0,
      };
    },
    refetchInterval: 60000,
  });

  // ============================================================
  // API Queries - Repair Configurations
  // ============================================================

  const { data: repairConfigs, isLoading: configsLoading, refetch: refetchConfigs } = useQuery<RepairConfiguration[]>({
    queryKey: ['repair-configurations'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/repair/configuration');
      return resp.data?.items || [];
    },
    enabled: activeSection === 'config',
  });

  // ============================================================
  // API Queries - Repair History
  // ============================================================

  const { data: repairHistory, isLoading: historyLoading, refetch: refetchHistory } = useQuery<RepairHistoryItem[]>({
    queryKey: ['repair-history'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/repair/history?limit=100');
      return resp.data?.items || [];
    },
    enabled: activeSection === 'history',
  });

  // ============================================================
  // API Queries - Repair Scripts
  // ============================================================

  const { data: repairScripts, isLoading: scriptsLoading, refetch: refetchScripts } = useQuery<RepairScript[]>({
    queryKey: ['repair-scripts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/repair/scripts');
      return resp.data?.items || [];
    },
    enabled: activeSection === 'templates',
  });

  // ============================================================
  // API Queries - Repair Effectiveness
  // ============================================================

  const { data: repairEffectiveness, isLoading: effectivenessLoading, refetch: refetchEffectiveness } = useQuery<RepairEffectiveness[]>({
    queryKey: ['repair-effectiveness'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/repair/effectiveness');
      return resp.data?.items || [];
    },
    enabled: activeSection === 'risk',
  });

  // ============================================================
  // Mutations
  // ============================================================

  const approveTaskMutation = useMutation({
    mutationFn: async (alertId: string) => {
      const resp = await api.patch(`/api/v1/approvals/${alertId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Task approved successfully');
      queryClient.invalidateQueries({ queryKey: ['heal-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['heal-statistics'] });
    },
    onError: (error: any) => {
      showError(`Failed to approve task: ${error.response?.data?.detail || error.message}`);
    },
  });

  const rejectTaskMutation = useMutation({
    mutationFn: async ({ alertId, reason }: { alertId: string; reason: string }) => {
      const resp = await api.post('/api/v1/approvals/reject', { alert_id: alertId, reason });
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Task rejected successfully');
      queryClient.invalidateQueries({ queryKey: ['heal-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['heal-statistics'] });
    },
    onError: (error: any) => {
      showError(`Failed to reject task: ${error.response?.data?.detail || error.message}`);
    },
  });

  const executeTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      const resp = await api.patch(`/api/v1/approvals/${taskId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Task execution started');
      queryClient.invalidateQueries({ queryKey: ['heal-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['heal-statistics'] });
    },
    onError: (error: any) => {
      showError(`Failed to execute task: ${error.response?.data?.detail || error.message}`);
    },
  });

  const createConfigMutation = useMutation({
    mutationFn: async (config: Partial<RepairConfiguration>) => {
      const resp = await api.post('/api/v1/repair/configuration', config);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Configuration created successfully');
      queryClient.invalidateQueries({ queryKey: ['repair-configurations'] });
      setConfigFormOpen(false);
    },
    onError: (error: any) => {
      showError(`Failed to create configuration: ${error.response?.data?.detail || error.message}`);
    },
  });

  const updateConfigMutation = useMutation({
    mutationFn: async ({ configId, config }: { configId: string; config: Partial<RepairConfiguration> }) => {
      const resp = await api.patch(`/api/v1/repair/configuration/${configId}`, config);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Configuration updated successfully');
      queryClient.invalidateQueries({ queryKey: ['repair-configurations'] });
      setConfigFormOpen(false);
      setSelectedConfig(null);
    },
    onError: (error: any) => {
      showError(`Failed to update configuration: ${error.response?.data?.detail || error.message}`);
    },
  });

  const deleteConfigMutation = useMutation({
    mutationFn: async (configId: string) => {
      const resp = await api.delete(`/api/v1/repair/configuration/${configId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Configuration deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['repair-configurations'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete configuration: ${error.response?.data?.detail || error.message}`);
    },
  });

  const createScriptMutation = useMutation({
    mutationFn: async (script: Partial<RepairScript>) => {
      const resp = await api.post('/api/v1/repair/scripts', script);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Script created successfully');
      queryClient.invalidateQueries({ queryKey: ['repair-scripts'] });
      setScriptFormOpen(false);
    },
    onError: (error: any) => {
      showError(`Failed to create script: ${error.response?.data?.detail || error.message}`);
    },
  });

  const updateScriptMutation = useMutation({
    mutationFn: async ({ scriptId, script }: { scriptId: string; script: Partial<RepairScript> }) => {
      const resp = await api.patch(`/api/v1/repair/scripts/${scriptId}`, script);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Script updated successfully');
      queryClient.invalidateQueries({ queryKey: ['repair-scripts'] });
      setScriptFormOpen(false);
      setSelectedScript(null);
    },
    onError: (error: any) => {
      showError(`Failed to update script: ${error.response?.data?.detail || error.message}`);
    },
  });

  const deleteScriptMutation = useMutation({
    mutationFn: async (scriptId: string) => {
      const resp = await api.delete(`/api/v1/repair/scripts/${scriptId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Script deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['repair-scripts'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete script: ${error.response?.data?.detail || error.message}`);
    },
  });

  // ============================================================
  // Effects
  // ============================================================

  useEffect(() => {
    if (tasksError) {
      setPageError(tasksError as Error);
      showError('Failed to load heal tasks');
    }
  }, [tasksError, setPageError, showError]);

  // ============================================================
  // Handlers
  // ============================================================

  const filteredTasks = healTasks?.filter((task) => {
    const matchesStatus = task.status === selectedTab;
    const matchesSearch = searchQuery === '' ||
      task.alertTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
      task.alertId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      task.healPlan.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRisk = filterRiskLevel === 'all' || task.riskLevel === filterRiskLevel;
    return matchesStatus && matchesSearch && matchesRisk;
  }) || [];

  const filteredHistory = repairHistory?.filter((item) => {
    const matchesSearch = searchQuery === '' ||
      item.repair_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.target_resource.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  }) || [];

  const filteredScripts = repairScripts?.filter((script) => {
    const matchesSearch = searchQuery === '' ||
      script.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      script.category.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  }) || [];

  const filteredConfigs = repairConfigs?.filter((config) => {
    const matchesSearch = searchQuery === '' ||
      config.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      config.key.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  }) || [];

  const handleApprove = async () => {
    if (!selectedTask) return;
    approveTaskMutation.mutate(selectedTask.alertId);
    setSelectedTask(null);
    setApprovalComment('');
  };

  const handleReject = async () => {
    if (!selectedTask) return;
    rejectTaskMutation.mutate({
      alertId: selectedTask.alertId,
      reason: approvalComment || '人工驳回',
    });
    setSelectedTask(null);
    setApprovalComment('');
  };

  const handleExecute = async (taskId: string) => {
    executeTaskMutation.mutate(taskId);
  };

  const handleCreateConfig = (config: Partial<RepairConfiguration>) => {
    createConfigMutation.mutate(config);
  };

  const handleUpdateConfig = (config: Partial<RepairConfiguration>) => {
    if (selectedConfig) {
      updateConfigMutation.mutate({ configId: selectedConfig.id, config });
    }
  };

  const handleDeleteConfig = (configId: string) => {
    if (confirm('Are you sure you want to delete this configuration?')) {
      deleteConfigMutation.mutate(configId);
    }
  };

  const handleCreateScript = (script: Partial<RepairScript>) => {
    createScriptMutation.mutate(script);
  };

  const handleUpdateScript = (script: Partial<RepairScript>) => {
    if (selectedScript) {
      updateScriptMutation.mutate({ scriptId: selectedScript.id, script });
    }
  };

  const handleDeleteScript = (scriptId: string) => {
    if (confirm('Are you sure you want to delete this script?')) {
      deleteScriptMutation.mutate(scriptId);
    }
  };

  // ============================================================
  // Helper Functions
  // ============================================================

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'critical':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-gray-100 text-gray-800';
      case 'approved':
        return 'bg-blue-100 text-blue-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'executing':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'pending' as const, label: '待审批', count: healStats?.pending_tasks || 0 },
    { key: 'approved' as const, label: '已批准', count: healStats?.approved_tasks || 0 },
    { key: 'executing' as const, label: '执行中', count: healStats?.executing_tasks || 0 },
    { key: 'completed' as const, label: '已完成', count: healStats?.completed_tasks || 0 },
    { key: 'failed' as const, label: '失败', count: healStats?.failed_tasks || 0 },
  ];

  // ============================================================
  // Loading and Error States
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
          description="无法加载自动修复数据，请稍后重试"
          action={<Button onClick={() => refetchTasks()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchTasks()}>重试</Button>}
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
          <Wrench className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">自动修复</h1>
            <p className="text-sm text-gray-500">自动化故障修复和审批流程管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchTasks()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* Statistics Cards */}
      {healStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">总任务数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-gray-900">{healStats.total_tasks}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">成功率</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{(healStats.success_rate * 100).toFixed(1)}%</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">平均执行时间</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">{Math.floor(healStats.avg_execution_time / 60)}m</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">待审批</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-yellow-600">{healStats.pending_tasks}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Navigation Tabs */}
      <Tabs value={activeSection} onValueChange={(v) => setActiveSection(v as any)} className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="tasks" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            修复任务
          </TabsTrigger>
          <TabsTrigger value="config" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            策略配置
          </TabsTrigger>
          <TabsTrigger value="risk" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            风险评估
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            修复历史
          </TabsTrigger>
          <TabsTrigger value="templates" className="flex items-center gap-2">
            <Code className="h-4 w-4" />
            脚本模板
          </TabsTrigger>
        </TabsList>

        {/* Tasks Section */}
        <TabsContent value="tasks" className="space-y-4">
          {/* Search and Filter Bar */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <Input
                    placeholder="搜索告警、ID或修复方案..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full"
                  />
                </div>
                <div className="flex gap-2">
                  <Select
                    value={filterRiskLevel}
                    onChange={(e) => setFilterRiskLevel(e.target.value)}
                    className="w-[150px]"
                  >
                    <option value="all">全部风险</option>
                    <option value="low">低风险</option>
                    <option value="medium">中风险</option>
                    <option value="high">高风险</option>
                    <option value="critical">严重风险</option>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Status Tabs */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex gap-2">
                {tabs.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setSelectedTab(tab.key)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${selectedTab === tab.key
                      ? 'bg-[var(--accent-blue)] text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                  >
                    {tab.key === 'pending' && <Clock className="h-4 w-4" />}
                    {tab.key === 'approved' && <CheckCircle className="h-4 w-4" />}
                    {tab.key === 'executing' && <Play className="h-4 w-4" />}
                    {tab.key === 'completed' && <CheckCircle className="h-4 w-4" />}
                    {tab.key === 'failed' && <XCircle className="h-4 w-4" />}
                    {tab.label} ({tab.count})
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Tasks Table */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  {selectedTab === 'pending' ? '待审批' : selectedTab === 'approved' ? '已批准' : selectedTab === 'executing' ? '执行中' : selectedTab === 'completed' ? '已完成' : '失败'}任务
                </div>
                <div className="text-sm text-gray-500">
                  显示 {filteredTasks.length} / {healTasks?.length || 0} 条记录
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {tasksLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : filteredTasks.length === 0 ? (
                <EmptyState
                  title="没有任务"
                  description={searchQuery || filterRiskLevel !== 'all' ? '没有匹配的任务，请调整搜索条件' : `当前没有${selectedTab === 'pending' ? '待审批' : selectedTab === 'approved' ? '已批准' : selectedTab === 'executing' ? '执行中' : selectedTab === 'completed' ? '已完成' : '失败'}任务`}
                  action={searchQuery || filterRiskLevel !== 'all' ? <Button onClick={() => { setSearchQuery(''); setFilterRiskLevel('all'); }}>清除筛选</Button> : undefined}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>告警</TableHead>
                      <TableHead>修复方案</TableHead>
                      <TableHead>风险等级</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>审批人</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTasks.map((task) => (
                      <TableRow key={task.id}>
                        <TableCell className="font-mono text-sm">{task.id}</TableCell>
                        <TableCell>
                          <div>
                            <p className="font-medium">{task.alertTitle}</p>
                            <p className="text-sm text-gray-500">{task.alertId}</p>
                          </div>
                        </TableCell>
                        <TableCell className="max-w-md truncate">{task.healPlan}</TableCell>
                        <TableCell>
                          <Badge className={getRiskColor(task.riskLevel)}>
                            {task.riskLevel === 'low' ? '低' : task.riskLevel === 'medium' ? '中' : task.riskLevel === 'high' ? '高' : '严重'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(task.status)}>
                            {task.status === 'pending' ? '待审批' :
                              task.status === 'approved' ? '已批准' :
                                task.status === 'rejected' ? '已拒绝' :
                                  task.status === 'completed' ? '已完成' : '失败'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(task.createdAt).toLocaleString()}
                        </TableCell>
                        <TableCell>{task.approver || '-'}</TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            {task.status === 'pending' && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setSelectedTask(task)}
                              >
                                审批
                              </Button>
                            )}
                            {task.status === 'approved' && (
                              <Button
                                size="sm"
                                onClick={() => handleExecute(task.id)}
                                disabled={executeTaskMutation.isPending}
                              >
                                {executeTaskMutation.isPending ? '执行中...' : '执行'}
                              </Button>
                            )}
                            {task.status === 'completed' && (
                              <Button variant="ghost" size="sm">
                                <FileText className="h-4 w-4 mr-1" />
                                查看日志
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Configuration Section */}
        <TabsContent value="config" className="space-y-4">
          {/* Search Bar */}
          <Card>
            <CardContent className="pt-6">
              <Input
                placeholder="搜索配置名称、键或类别..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  修复策略配置
                </CardTitle>
                <Button onClick={() => { setSelectedConfig(null); setConfigFormOpen(true); }} size="sm">
                  新增配置
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {configsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !filteredConfigs || filteredConfigs.length === 0 ? (
                <EmptyState
                  title="暂无配置"
                  description={searchQuery ? '没有匹配的配置' : '还没有创建修复策略配置'}
                  action={searchQuery ? <Button onClick={() => setSearchQuery('')}>清除搜索</Button> : undefined}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>键</TableHead>
                      <TableHead>类别</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>更新时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredConfigs.map((config) => (
                      <TableRow key={config.id}>
                        <TableCell className="font-medium">{config.name}</TableCell>
                        <TableCell>{config.config_type}</TableCell>
                        <TableCell className="font-mono text-sm">{config.key}</TableCell>
                        <TableCell>{config.category}</TableCell>
                        <TableCell>
                          <Badge className={config.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {config.is_active ? '启用' : '禁用'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(config.updated_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => { setSelectedConfig(config); setConfigFormOpen(true); }}
                            >
                              编辑
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleDeleteConfig(config.id)}
                            >
                              删除
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Risk Assessment Section */}
        <TabsContent value="risk" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                修复风险评估
              </CardTitle>
            </CardHeader>
            <CardContent>
              {effectivenessLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !repairEffectiveness || repairEffectiveness.length === 0 ? (
                <EmptyState
                  title="暂无数据"
                  description="还没有修复效果评估数据"
                />
              ) : (
                <>
                  {/* Summary Statistics */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600">平均成功率</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold text-green-600">
                          {(repairEffectiveness.reduce((sum, e) => sum + e.success_rate, 0) / repairEffectiveness.length).toFixed(1)}%
                        </div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600">总修复次数</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold text-gray-900">
                          {repairEffectiveness.reduce((sum, e) => sum + e.total_repairs, 0)}
                        </div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600">平均修复时间</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold text-blue-600">
                          {(repairEffectiveness.reduce((sum, e) => sum + e.avg_repair_time, 0) / repairEffectiveness.length).toFixed(1)}s
                        </div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-gray-600">改善趋势</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold text-green-600">
                          {repairEffectiveness.filter(e => e.trend === 'improving').length}
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Effectiveness Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {repairEffectiveness.map((effectiveness) => (
                      <Card key={effectiveness.id}>
                        <CardHeader>
                          <CardTitle className="text-lg">{effectiveness.repair_type}</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-sm text-gray-500">成功率</p>
                              <p className="text-2xl font-bold text-green-600">{effectiveness.success_rate.toFixed(1)}%</p>
                            </div>
                            <div>
                              <p className="text-sm text-gray-500">平均修复时间</p>
                              <p className="text-2xl font-bold text-blue-600">{effectiveness.avg_repair_time.toFixed(1)}s</p>
                            </div>
                            <div>
                              <p className="text-sm text-gray-500">总修复次数</p>
                              <p className="text-2xl font-bold text-gray-900">{effectiveness.total_repairs}</p>
                            </div>
                            <div>
                              <p className="text-sm text-gray-500">成功/失败</p>
                              <p className="text-sm font-medium">
                                <span className="text-green-600">{effectiveness.successful_repairs}</span>
                                <span className="text-gray-400"> / </span>
                                <span className="text-red-600">{effectiveness.failed_repairs}</span>
                              </p>
                            </div>
                          </div>
                          <div className="pt-4 border-t">
                            <div className="flex items-center justify-between mb-2">
                              <p className="text-sm text-gray-500">趋势</p>
                              <Badge className={
                                effectiveness.trend === 'improving' ? 'bg-green-100 text-green-800' :
                                  effectiveness.trend === 'degrading' ? 'bg-red-100 text-red-800' :
                                    'bg-gray-100 text-gray-800'
                              }>
                                {effectiveness.trend === 'improving' ? '改善' :
                                  effectiveness.trend === 'degrading' ? '下降' : '稳定'}
                              </Badge>
                            </div>
                            <p className="text-sm text-gray-500">目标资源: {effectiveness.target_resource}</p>
                            <p className="text-sm text-gray-500">最后评估: {new Date(effectiveness.last_evaluated).toLocaleString()}</p>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* History Section */}
        <TabsContent value="history" className="space-y-4">
          {/* Search and Filter Bar */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <Input
                    placeholder="搜索修复类型或目标资源..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full"
                  />
                </div>
                <div className="flex gap-2">
                  <Select
                    value={filterDateRange}
                    onChange={(e) => setFilterDateRange(e.target.value)}
                    className="w-[150px]"
                  >
                    <option value="all">全部时间</option>
                    <option value="today">今天</option>
                    <option value="week">本周</option>
                    <option value="month">本月</option>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <History className="h-5 w-5" />
                  修复历史分析
                </div>
                <div className="text-sm text-gray-500">
                  显示 {filteredHistory.length} / {repairHistory?.length || 0} 条记录
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {historyLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !filteredHistory || filteredHistory.length === 0 ? (
                <EmptyState
                  title="暂无历史"
                  description={searchQuery ? '没有匹配的历史记录' : '还没有修复历史记录'}
                  action={searchQuery ? <Button onClick={() => setSearchQuery('')}>清除搜索</Button> : undefined}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>修复类型</TableHead>
                      <TableHead>目标资源</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>开始时间</TableHead>
                      <TableHead>执行者</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredHistory.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-mono text-sm">{item.id}</TableCell>
                        <TableCell>{item.repair_type}</TableCell>
                        <TableCell>{item.target_resource}</TableCell>
                        <TableCell>
                          <Badge className={item.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                            {item.status === 'success' ? '成功' : '失败'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(item.start_time).toLocaleString()}
                        </TableCell>
                        <TableCell>{item.executed_by}</TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => { setSelectedHistoryItem(item); setHistoryDetailOpen(true); }}
                          >
                            <FileText className="h-4 w-4 mr-1" />
                            详情
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Templates Section */}
        <TabsContent value="templates" className="space-y-4">
          {/* Search Bar */}
          <Card>
            <CardContent className="pt-6">
              <Input
                placeholder="搜索脚本名称或类别..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Code className="h-5 w-5" />
                  修复脚本模板管理
                </CardTitle>
                <Button onClick={() => { setSelectedScript(null); setScriptFormOpen(true); }} size="sm">
                  新增脚本
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {scriptsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !filteredScripts || filteredScripts.length === 0 ? (
                <EmptyState
                  title="暂无脚本"
                  description={searchQuery ? '没有匹配的脚本' : '还没有创建修复脚本模板'}
                  action={searchQuery ? <Button onClick={() => setSearchQuery('')}>清除搜索</Button> : undefined}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead>语言</TableHead>
                      <TableHead>平台</TableHead>
                      <TableHead>类别</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredScripts.map((script) => (
                      <TableRow key={script.id}>
                        <TableCell className="font-medium">{script.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{script.language}</Badge>
                        </TableCell>
                        <TableCell>{script.platform}</TableCell>
                        <TableCell>{script.category}</TableCell>
                        <TableCell>
                          <Badge className={script.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {script.status === 'active' ? '启用' : '禁用'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(script.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => { setSelectedScript(script); setScriptFormOpen(true); }}
                            >
                              编辑
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleDeleteScript(script.id)}
                            >
                              删除
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Approval Dialog */}
      {selectedTask && (
        <Dialog open={!!selectedTask} onOpenChange={() => setSelectedTask(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                审批修复任务 - {selectedTask.id}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">告警信息</label>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="font-medium text-gray-900">{selectedTask.alertTitle}</p>
                  <p className="text-sm text-gray-500 font-mono">{selectedTask.alertId}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">修复方案</label>
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm text-gray-900 whitespace-pre-wrap">{selectedTask.healPlan}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">风险等级</label>
                <Badge className={getRiskColor(selectedTask.riskLevel)}>
                  {selectedTask.riskLevel === 'low' ? '低风险' : selectedTask.riskLevel === 'medium' ? '中风险' : selectedTask.riskLevel === 'high' ? '高风险' : '严重风险'}
                </Badge>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">审批意见</label>
                <Textarea
                  value={approvalComment}
                  onChange={(e) => setApprovalComment(e.target.value)}
                  placeholder="请输入审批意见（可选）..."
                  rows={3}
                />
              </div>
              {(selectedTask.riskLevel === 'high' || selectedTask.riskLevel === 'critical') && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-800">⚠️ 高风险操作警告</p>
                      <p className="text-sm text-red-700 mt-1">此操作可能对系统产生重大影响，请仔细审查修复方案后再进行审批。</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setSelectedTask(null)}>
                取消
              </Button>
              <Button
                variant="destructive"
                onClick={handleReject}
                disabled={rejectTaskMutation.isPending}
              >
                {rejectTaskMutation.isPending ? '驳回中...' : '拒绝'}
              </Button>
              <Button
                onClick={handleApprove}
                disabled={approveTaskMutation.isPending}
              >
                {approveTaskMutation.isPending ? '批准中...' : '批准'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Configuration Form Dialog */}
      {configFormOpen && (
        <Dialog open={configFormOpen} onOpenChange={setConfigFormOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>
                {selectedConfig ? '编辑配置' : '新增配置'}
              </DialogTitle>
            </DialogHeader>
            <ConfigurationForm
              config={selectedConfig}
              onSubmit={selectedConfig ? handleUpdateConfig : handleCreateConfig}
              onCancel={() => setConfigFormOpen(false)}
              isSubmitting={createConfigMutation.isPending || updateConfigMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      )}

      {/* Script Form Dialog */}
      {scriptFormOpen && (
        <Dialog open={scriptFormOpen} onOpenChange={setScriptFormOpen}>
          <DialogContent className="max-w-3xl">
            <DialogHeader>
              <DialogTitle>
                {selectedScript ? '编辑脚本' : '新增脚本'}
              </DialogTitle>
            </DialogHeader>
            <ScriptForm
              script={selectedScript}
              onSubmit={selectedScript ? handleUpdateScript : handleCreateScript}
              onCancel={() => setScriptFormOpen(false)}
              isSubmitting={createScriptMutation.isPending || updateScriptMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      )}

      {/* History Detail Dialog */}
      {historyDetailOpen && selectedHistoryItem && (
        <Dialog open={historyDetailOpen} onOpenChange={setHistoryDetailOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                修复历史详情
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">修复类型</label>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="font-medium">{selectedHistoryItem.repair_type}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">目标资源</label>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="font-mono text-sm">{selectedHistoryItem.target_resource}</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">问题描述</label>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm">{selectedHistoryItem.issue_description}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Badge className={selectedHistoryItem.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                    {selectedHistoryItem.status === 'success' ? '成功' : '失败'}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">执行时间</label>
                  <p className="text-sm text-gray-900">
                    {selectedHistoryItem.duration ? `${selectedHistoryItem.duration}秒` : 'N/A'}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">开始时间</label>
                  <p className="text-sm text-gray-500">
                    {new Date(selectedHistoryItem.start_time).toLocaleString()}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">结束时间</label>
                  <p className="text-sm text-gray-500">
                    {new Date(selectedHistoryItem.end_time).toLocaleString()}
                  </p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">执行者</label>
                <p className="text-sm text-gray-900">{selectedHistoryItem.executed_by}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">详细信息</label>
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm whitespace-pre-wrap">{selectedHistoryItem.details}</p>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setHistoryDetailOpen(false)}>
                关闭
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

// ============================================================
// Sub-Components
// ============================================================

interface ConfigurationFormProps {
  config: RepairConfiguration | null;
  onSubmit: (config: Partial<RepairConfiguration>) => void;
  onCancel: () => void;
  isSubmitting: boolean;
}

function ConfigurationForm({ config, onSubmit, onCancel, isSubmitting }: ConfigurationFormProps) {
  const [formData, setFormData] = useState<Partial<RepairConfiguration>>(
    config || {
      name: '',
      description: '',
      config_type: 'global',
      key: '',
      value: '',
      category: 'default',
      is_secret: false,
      is_active: true,
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="name">名称</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          required
        />
      </div>
      <div>
        <Label htmlFor="description">描述</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          rows={3}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="config_type">类型</Label>
          <Select
            id="config_type"
            value={formData.config_type}
            onChange={(e) => setFormData({ ...formData, config_type: e.target.value })}
          >
            <option value="global">全局</option>
            <option value="platform">平台</option>
            <option value="resource">资源</option>
            <option value="script">脚本</option>
          </Select>
        </div>
        <div>
          <Label htmlFor="category">类别</Label>
          <Input
            id="category"
            value={formData.category}
            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="key">键</Label>
          <Input
            id="key"
            value={formData.key}
            onChange={(e) => setFormData({ ...formData, key: e.target.value })}
            required
          />
        </div>
        <div>
          <Label htmlFor="value">值</Label>
          <Input
            id="value"
            value={formData.value}
            onChange={(e) => setFormData({ ...formData, value: e.target.value })}
            required
            type={formData.is_secret ? 'password' : 'text'}
          />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_secret"
          checked={formData.is_secret}
          onChange={(e) => setFormData({ ...formData, is_secret: e.target.checked })}
        />
        <Label htmlFor="is_secret">敏感信息</Label>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? '提交中...' : '提交'}
        </Button>
      </DialogFooter>
    </form>
  );
}

interface ScriptFormProps {
  script: RepairScript | null;
  onSubmit: (script: Partial<RepairScript>) => void;
  onCancel: () => void;
  isSubmitting: boolean;
}

function ScriptForm({ script, onSubmit, onCancel, isSubmitting }: ScriptFormProps) {
  const [formData, setFormData] = useState<Partial<RepairScript>>(
    script || {
      name: '',
      description: '',
      language: 'bash',
      platform: 'linux',
      category: 'general',
      content: '',
      status: 'active',
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="name">名称</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          required
        />
      </div>
      <div>
        <Label htmlFor="description">描述</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          rows={3}
        />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <Label htmlFor="language">语言</Label>
          <Select
            id="language"
            value={formData.language}
            onChange={(e) => setFormData({ ...formData, language: e.target.value })}
          >
            <option value="bash">Bash</option>
            <option value="python">Python</option>
            <option value="powershell">PowerShell</option>
            <option value="javascript">JavaScript</option>
          </Select>
        </div>
        <div>
          <Label htmlFor="platform">平台</Label>
          <Select
            id="platform"
            value={formData.platform}
            onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
          >
            <option value="linux">Linux</option>
            <option value="windows">Windows</option>
            <option value="macos">macOS</option>
            <option value="docker">Docker</option>
            <option value="kubernetes">Kubernetes</option>
          </Select>
        </div>
        <div>
          <Label htmlFor="category">类别</Label>
          <Input
            id="category"
            value={formData.category}
            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
          />
        </div>
      </div>
      <div>
        <Label htmlFor="content">脚本内容</Label>
        <Textarea
          id="content"
          value={formData.content}
          onChange={(e) => setFormData({ ...formData, content: e.target.value })}
          rows={10}
          className="font-mono text-sm"
          required
        />
      </div>
      <div>
        <Label htmlFor="status">状态</Label>
        <Select
          id="status"
          value={formData.status}
          onChange={(e) => setFormData({ ...formData, status: e.target.value })}
        >
          <option value="active">启用</option>
          <option value="inactive">禁用</option>
          <option value="deprecated">已弃用</option>
        </Select>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? '提交中...' : '提交'}
        </Button>
      </DialogFooter>
    </form>
  );
}
