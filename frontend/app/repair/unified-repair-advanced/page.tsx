'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { 
  Wrench, 
  Play, 
  Pause, 
  Trash2, 
  Edit, 
  Plus, 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  Clock,
  Server,
  Cpu,
  Globe,
  BarChart3,
  FileText,
  Settings,
  Zap
} from 'lucide-react';
import api from '@/lib/api';

// ============================================================
// Type Definitions
// ============================================================

interface RepairStrategy {
  id: string;
  name: string;
  description: string;
  repair_type: string;
  target_scope: string;
  platform: string;
  script_content?: string;
  config_changes?: Record<string, any>;
  priority: string;
  auto_approve: boolean;
  status: string;
  metadata: Record<string, any>;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
  execution_count?: number;
  success_count?: number;
  failure_count?: number;
}

interface RepairExecution {
  id: string;
  strategy_id: string;
  strategy_name: string;
  target_resource: string;
  parameters: Record<string, any>;
  requested_by: string;
  reason: string;
  status: string;
  result?: Record<string, any>;
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  target_platforms?: string[];
  target_resources?: Record<string, string>;
  parallel?: boolean;
  results?: Array<{
    platform: string;
    status: string;
    result?: Record<string, any>;
    error?: string;
  }>;
}

interface Platform {
  id: string;
  name: string;
  type: string;
  endpoint?: string;
  credentials?: Record<string, string>;
  capabilities: string[];
  metadata: Record<string, any>;
  status: string;
  created_at: string;
  created_by: string;
  updated_at: string;
}

interface RepairTemplate {
  id: string;
  name: string;
  description: string;
  repair_type: string;
  platform: string;
  template_content: string;
  parameters: Array<Record<string, any>>;
  category: string;
  status: string;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
}

interface RepairAnalytics {
  time_range: string;
  summary: {
    total_executions: number;
    successful_executions: number;
    failed_executions: number;
    pending_executions: number;
    running_executions: number;
    success_rate: number;
    avg_duration_seconds: number;
  };
  platform_breakdown: Record<string, { total: number; success: number; failed: number }>;
  type_breakdown: Record<string, { total: number; success: number; failed: number }>;
  top_strategies: Array<{
    strategy_id: string;
    strategy_name: string;
    execution_count: number;
  }>;
  generated_at: string;
}

// ============================================================
// Main Component
// ============================================================

export default function UnifiedRepairAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'strategies' | 'executions' | 'platforms' | 'templates' | 'analytics'>('strategies');
  const [selectedStrategy, setSelectedStrategy] = useState<RepairStrategy | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<RepairExecution | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<RepairTemplate | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isExecuteDialogOpen, setIsExecuteDialogOpen] = useState(false);
  const [isCrossPlatformDialogOpen, setIsCrossPlatformDialogOpen] = useState(false);

  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // ============================================================
  // API Queries
  // ============================================================

  // Fetch repair strategies
  const { data: strategies, isLoading: strategiesLoading, error: strategiesError, refetch: refetchStrategies } = useQuery<RepairStrategy[]>({
    queryKey: ['repair-strategies'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/unified-repair/strategies');
      return resp.data?.items || [];
    },
    refetchInterval: 30000,
  });

  // Fetch repair executions
  const { data: executions, isLoading: executionsLoading, error: executionsError, refetch: refetchExecutions } = useQuery<RepairExecution[]>({
    queryKey: ['repair-executions'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/unified-repair/executions');
      return resp.data?.items || [];
    },
    refetchInterval: 15000,
  });

  // Fetch platforms
  const { data: platforms, isLoading: platformsLoading, error: platformsError, refetch: refetchPlatforms } = useQuery<Platform[]>({
    queryKey: ['repair-platforms'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/unified-repair/platforms');
      return resp.data?.items || [];
    },
    refetchInterval: 60000,
  });

  // Fetch templates
  const { data: templates, isLoading: templatesLoading, error: templatesError, refetch: refetchTemplates } = useQuery<RepairTemplate[]>({
    queryKey: ['repair-templates'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/unified-repair/templates');
      return resp.data?.items || [];
    },
    refetchInterval: 60000,
  });

  // Fetch analytics
  const { data: analytics, isLoading: analyticsLoading, error: analyticsError, refetch: refetchAnalytics } = useQuery<RepairAnalytics>({
    queryKey: ['repair-analytics'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/unified-repair/analytics?time_range=7d');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  // ============================================================
  // API Mutations
  // ============================================================

  // Create strategy mutation
  const createStrategyMutation = useMutation({
    mutationFn: async (data: Partial<RepairStrategy>) => {
      const resp = await api.post('/api/v1/unified-repair/strategies', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('修复策略创建成功');
      queryClient.invalidateQueries({ queryKey: ['repair-strategies'] });
      setIsCreateDialogOpen(false);
    },
    onError: (error: any) => {
      showError(`创建失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Update strategy mutation
  const updateStrategyMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<RepairStrategy> }) => {
      const resp = await api.patch(`/api/v1/unified-repair/strategies/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('修复策略更新成功');
      queryClient.invalidateQueries({ queryKey: ['repair-strategies'] });
      setIsEditDialogOpen(false);
      setSelectedStrategy(null);
    },
    onError: (error: any) => {
      showError(`更新失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete strategy mutation
  const deleteStrategyMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/unified-repair/strategies/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('修复策略删除成功');
      queryClient.invalidateQueries({ queryKey: ['repair-strategies'] });
    },
    onError: (error: any) => {
      showError(`删除失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Create execution mutation
  const createExecutionMutation = useMutation({
    mutationFn: async (data: { strategy_id: string; target_resource: string; parameters?: Record<string, any>; reason?: string }) => {
      const resp = await api.post('/api/v1/unified-repair/executions', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('修复执行创建成功');
      queryClient.invalidateQueries({ queryKey: ['repair-executions'] });
      queryClient.invalidateQueries({ queryKey: ['repair-analytics'] });
      setIsExecuteDialogOpen(false);
    },
    onError: (error: any) => {
      showError(`执行失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Update execution mutation
  const updateExecutionMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<RepairExecution> }) => {
      const resp = await api.patch(`/api/v1/unified-repair/executions/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('修复执行更新成功');
      queryClient.invalidateQueries({ queryKey: ['repair-executions'] });
      queryClient.invalidateQueries({ queryKey: ['repair-analytics'] });
    },
    onError: (error: any) => {
      showError(`更新失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete execution mutation
  const deleteExecutionMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/unified-repair/executions/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('修复执行删除成功');
      queryClient.invalidateQueries({ queryKey: ['repair-executions'] });
    },
    onError: (error: any) => {
      showError(`删除失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Create platform mutation
  const createPlatformMutation = useMutation({
    mutationFn: async (data: Partial<Platform>) => {
      const resp = await api.post('/api/v1/unified-repair/platforms', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('平台配置创建成功');
      queryClient.invalidateQueries({ queryKey: ['repair-platforms'] });
      setIsCreateDialogOpen(false);
    },
    onError: (error: any) => {
      showError(`创建失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete platform mutation
  const deletePlatformMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/unified-repair/platforms/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('平台配置删除成功');
      queryClient.invalidateQueries({ queryKey: ['repair-platforms'] });
    },
    onError: (error: any) => {
      showError(`删除失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Create template mutation
  const createTemplateMutation = useMutation({
    mutationFn: async (data: Partial<RepairTemplate>) => {
      const resp = await api.post('/api/v1/unified-repair/templates', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('修复模板创建成功');
      queryClient.invalidateQueries({ queryKey: ['repair-templates'] });
      setIsCreateDialogOpen(false);
    },
    onError: (error: any) => {
      showError(`创建失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Update template mutation
  const updateTemplateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<RepairTemplate> }) => {
      const resp = await api.patch(`/api/v1/unified-repair/templates/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('修复模板更新成功');
      queryClient.invalidateQueries({ queryKey: ['repair-templates'] });
      setIsEditDialogOpen(false);
      setSelectedTemplate(null);
    },
    onError: (error: any) => {
      showError(`更新失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete template mutation
  const deleteTemplateMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/unified-repair/templates/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('修复模板删除成功');
      queryClient.invalidateQueries({ queryKey: ['repair-templates'] });
    },
    onError: (error: any) => {
      showError(`删除失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Cross-platform repair mutation
  const crossPlatformRepairMutation = useMutation({
    mutationFn: async (data: { target_platforms: string[]; strategy_id: string; target_resources: Record<string, string>; parameters?: Record<string, any>; parallel?: boolean }) => {
      const resp = await api.post('/api/v1/unified-repair/cross-platform', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('跨平台修复执行成功');
      queryClient.invalidateQueries({ queryKey: ['repair-executions'] });
      queryClient.invalidateQueries({ queryKey: ['repair-analytics'] });
      setIsCrossPlatformDialogOpen(false);
    },
    onError: (error: any) => {
      showError(`执行失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // ============================================================
  // Event Handlers
  // ============================================================

  const handleCreateStrategy = (data: Partial<RepairStrategy>) => {
    createStrategyMutation.mutate(data);
  };

  const handleUpdateStrategy = (data: Partial<RepairStrategy>) => {
    if (selectedStrategy) {
      updateStrategyMutation.mutate({ id: selectedStrategy.id, data });
    }
  };

  const handleDeleteStrategy = (id: string) => {
    if (confirm('确定要删除此修复策略吗？')) {
      deleteStrategyMutation.mutate(id);
    }
  };

  const handleExecuteRepair = (strategyId: string, targetResource: string) => {
    createExecutionMutation.mutate({
      strategy_id: strategyId,
      target_resource: targetResource,
      reason: '手动执行',
    });
  };

  const handleDeleteExecution = (id: string) => {
    if (confirm('确定要删除此修复执行记录吗？')) {
      deleteExecutionMutation.mutate(id);
    }
  };

  const handleCreatePlatform = (data: Partial<Platform>) => {
    createPlatformMutation.mutate(data);
  };

  const handleDeletePlatform = (id: string) => {
    if (confirm('确定要删除此平台配置吗？')) {
      deletePlatformMutation.mutate(id);
    }
  };

  const handleCreateTemplate = (data: Partial<RepairTemplate>) => {
    createTemplateMutation.mutate(data);
  };

  const handleUpdateTemplate = (data: Partial<RepairTemplate>) => {
    if (selectedTemplate) {
      updateTemplateMutation.mutate({ id: selectedTemplate.id, data });
    }
  };

  const handleDeleteTemplate = (id: string) => {
    if (confirm('确定要删除此修复模板吗？')) {
      deleteTemplateMutation.mutate(id);
    }
  };

  const handleCrossPlatformRepair = (data: { target_platforms: string[]; strategy_id: string; target_resources: Record<string, string>; parameters?: Record<string, any>; parallel?: boolean }) => {
    crossPlatformRepairMutation.mutate(data);
  };

  // ============================================================
  // Helper Functions
  // ============================================================

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'deprecated':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'low':
        return 'bg-blue-100 text-blue-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'critical':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPlatformIcon = (type: string) => {
    switch (type) {
      case 'linux':
        return <Server className="h-4 w-4" />;
      case 'windows':
        return <Cpu className="h-4 w-4" />;
      case 'docker':
        return <Zap className="h-4 w-4" />;
      case 'kubernetes':
        return <Globe className="h-4 w-4" />;
      case 'cloud':
        return <Globe className="h-4 w-4" />;
      default:
        return <Server className="h-4 w-4" />;
    }
  };

  // ============================================================
  // Error Handling
  // ============================================================

  useEffect(() => {
    if (strategiesError) {
      setPageError(strategiesError as Error);
      showError('加载修复策略失败');
    }
    if (executionsError) {
      setPageError(executionsError as Error);
      showError('加载修复执行失败');
    }
    if (platformsError) {
      setPageError(platformsError as Error);
      showError('加载平台配置失败');
    }
    if (templatesError) {
      setPageError(templatesError as Error);
      showError('加载修复模板失败');
    }
    if (analyticsError) {
      setPageError(analyticsError as Error);
      showError('加载修复分析失败');
    }
  }, [strategiesError, executionsError, platformsError, templatesError, analyticsError, setPageError, showError]);

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
          description="无法加载统一修复数据，请稍后重试"
          action={<Button onClick={() => {
            refetchStrategies();
            refetchExecutions();
            refetchPlatforms();
            refetchTemplates();
            refetchAnalytics();
          }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => {
            refetchStrategies();
            refetchExecutions();
            refetchPlatforms();
            refetchTemplates();
            refetchAnalytics();
          }}>重试</Button>}
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
            <h1 className="text-3xl font-bold text-gray-900">统一修复高级管理</h1>
            <p className="text-sm text-gray-500">跨平台修复策略、执行和效果评估</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => {
            refetchStrategies();
            refetchExecutions();
            refetchPlatforms();
            refetchTemplates();
            refetchAnalytics();
          }} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* Analytics Summary */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">总执行次数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-gray-900">{analytics.summary.total_executions}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">成功率</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{analytics.summary.success_rate.toFixed(1)}%</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">平均执行时间</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">{Math.floor(analytics.summary.avg_duration_seconds)}s</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">失败次数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-600">{analytics.summary.failed_executions}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="strategies">
            <Settings className="h-4 w-4 mr-2" />
            修复策略
          </TabsTrigger>
          <TabsTrigger value="executions">
            <Play className="h-4 w-4 mr-2" />
            修复执行
          </TabsTrigger>
          <TabsTrigger value="platforms">
            <Server className="h-4 w-4 mr-2" />
            平台配置
          </TabsTrigger>
          <TabsTrigger value="templates">
            <FileText className="h-4 w-4 mr-2" />
            修复模板
          </TabsTrigger>
          <TabsTrigger value="analytics">
            <BarChart3 className="h-4 w-4 mr-2" />
            效果评估
          </TabsTrigger>
        </TabsList>

        {/* Strategies Tab */}
        <TabsContent value="strategies" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>修复策略管理</CardTitle>
                <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  创建策略
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {strategiesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : strategies?.length === 0 ? (
                <EmptyState
                  title="没有修复策略"
                  description="点击创建按钮添加新的修复策略"
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>平台</TableHead>
                      <TableHead>优先级</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>执行次数</TableHead>
                      <TableHead>成功率</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {strategies?.map((strategy) => (
                      <TableRow key={strategy.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{strategy.name}</p>
                            <p className="text-sm text-gray-500">{strategy.description}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{strategy.repair_type}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getPlatformIcon(strategy.platform)}
                            <span className="capitalize">{strategy.platform}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={getPriorityColor(strategy.priority)}>
                            {strategy.priority}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(strategy.status)}>
                            {strategy.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{strategy.execution_count || 0}</TableCell>
                        <TableCell>
                          {strategy.execution_count && strategy.execution_count > 0
                            ? `${((strategy.success_count || 0) / strategy.execution_count * 100).toFixed(1)}%`
                            : '-'}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedStrategy(strategy);
                                setIsEditDialogOpen(true);
                              }}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteStrategy(strategy.id)}
                            >
                              <Trash2 className="h-4 w-4" />
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

        {/* Executions Tab */}
        <TabsContent value="executions" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>修复执行管理</CardTitle>
                <Button onClick={() => setIsExecuteDialogOpen(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  创建执行
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {executionsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : executions?.length === 0 ? (
                <EmptyState
                  title="没有修复执行"
                  description="点击创建按钮添加新的修复执行"
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>策略</TableHead>
                      <TableHead>目标资源</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>请求者</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>完成时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {executions?.map((execution) => (
                      <TableRow key={execution.id}>
                        <TableCell className="font-mono text-sm">{execution.id.slice(0, 8)}</TableCell>
                        <TableCell>
                          <div>
                            <p className="font-medium">{execution.strategy_name}</p>
                            <p className="text-sm text-gray-500">{execution.strategy_id.slice(0, 8)}</p>
                          </div>
                        </TableCell>
                        <TableCell>{execution.target_resource}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(execution.status)}>
                            {execution.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{execution.requested_by}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(execution.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {execution.completed_at ? new Date(execution.completed_at).toLocaleString() : '-'}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedExecution(execution)}
                            >
                              <FileText className="h-4 w-4" />
                            </Button>
                            {execution.status === 'pending' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => updateExecutionMutation.mutate({
                                  id: execution.id,
                                  data: { status: 'running' }
                                })}
                                disabled={updateExecutionMutation.isPending}
                              >
                                <Play className="h-4 w-4" />
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteExecution(execution.id)}
                            >
                              <Trash2 className="h-4 w-4" />
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

        {/* Platforms Tab */}
        <TabsContent value="platforms" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>平台配置管理</CardTitle>
                <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  添加平台
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {platformsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : platforms?.length === 0 ? (
                <EmptyState
                  title="没有平台配置"
                  description="点击添加按钮配置新的平台"
                />
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {platforms?.map((platform) => (
                    <Card key={platform.id}>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <CardTitle className="flex items-center gap-2">
                            {getPlatformIcon(platform.type)}
                            {platform.name}
                          </CardTitle>
                          <Badge className={getStatusColor(platform.status)}>
                            {platform.status}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-500">类型:</span>
                            <span className="font-medium capitalize">{platform.type}</span>
                          </div>
                          {platform.endpoint && (
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-500">端点:</span>
                              <span className="font-medium truncate ml-2">{platform.endpoint}</span>
                            </div>
                          )}
                          <div className="flex flex-wrap gap-1 mt-2">
                            {platform.capabilities.map((cap) => (
                              <Badge key={cap} variant="outline" className="text-xs">
                                {cap}
                              </Badge>
                            ))}
                          </div>
                          <div className="flex gap-2 mt-4">
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex-1"
                              onClick={() => handleDeletePlatform(platform.id)}
                            >
                              <Trash2 className="h-4 w-4 mr-1" />
                              删除
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>修复模板管理</CardTitle>
                <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  创建模板
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {templatesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : templates?.length === 0 ? (
                <EmptyState
                  title="没有修复模板"
                  description="点击创建按钮添加新的修复模板"
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>平台</TableHead>
                      <TableHead>分类</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {templates?.map((template) => (
                      <TableRow key={template.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{template.name}</p>
                            <p className="text-sm text-gray-500">{template.description}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{template.repair_type}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getPlatformIcon(template.platform)}
                            <span className="capitalize">{template.platform}</span>
                          </div>
                        </TableCell>
                        <TableCell>{template.category}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(template.status)}>
                            {template.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedTemplate(template);
                                setIsEditDialogOpen(true);
                              }}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteTemplate(template.id)}
                            >
                              <Trash2 className="h-4 w-4" />
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

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-4">
          {analyticsLoading ? (
            <Card>
              <CardContent className="flex items-center justify-center py-8">
                <LoadingSpinner />
              </CardContent>
            </Card>
          ) : analytics ? (
            <div className="space-y-4">
              {/* Platform Breakdown */}
              <Card>
                <CardHeader>
                  <CardTitle>平台分布</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>平台</TableHead>
                        <TableHead>总执行次数</TableHead>
                        <TableHead>成功次数</TableHead>
                        <TableHead>失败次数</TableHead>
                        <TableHead>成功率</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {Object.entries(analytics.platform_breakdown).map(([platform, stats]) => (
                        <TableRow key={platform}>
                          <TableCell className="capitalize">{platform}</TableCell>
                          <TableCell>{stats.total}</TableCell>
                          <TableCell>{stats.success}</TableCell>
                          <TableCell>{stats.failed}</TableCell>
                          <TableCell>
                            {stats.total > 0 ? `${((stats.success / stats.total) * 100).toFixed(1)}%` : '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              {/* Type Breakdown */}
              <Card>
                <CardHeader>
                  <CardTitle>修复类型分布</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>类型</TableHead>
                        <TableHead>总执行次数</TableHead>
                        <TableHead>成功次数</TableHead>
                        <TableHead>失败次数</TableHead>
                        <TableHead>成功率</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {Object.entries(analytics.type_breakdown).map(([type, stats]) => (
                        <TableRow key={type}>
                          <TableCell className="capitalize">{type}</TableCell>
                          <TableCell>{stats.total}</TableCell>
                          <TableCell>{stats.success}</TableCell>
                          <TableCell>{stats.failed}</TableCell>
                          <TableCell>
                            {stats.total > 0 ? `${((stats.success / stats.total) * 100).toFixed(1)}%` : '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              {/* Top Strategies */}
              <Card>
                <CardHeader>
                  <CardTitle>热门修复策略</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>策略名称</TableHead>
                        <TableHead>执行次数</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {analytics.top_strategies.map((strategy) => (
                        <TableRow key={strategy.strategy_id}>
                          <TableCell>{strategy.strategy_name}</TableCell>
                          <TableCell>{strategy.execution_count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          ) : (
            <EmptyState
              title="没有分析数据"
              description="暂无修复分析数据"
            />
          )}
        </TabsContent>
      </Tabs>

      {/* Create Strategy Dialog */}
      <Dialog open={isCreateDialogOpen && activeTab === 'strategies'} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>创建修复策略</DialogTitle>
          </DialogHeader>
          <StrategyForm onSubmit={handleCreateStrategy} onCancel={() => setIsCreateDialogOpen(false)} />
        </DialogContent>
      </Dialog>

      {/* Edit Strategy Dialog */}
      <Dialog open={isEditDialogOpen && activeTab === 'strategies'} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>编辑修复策略</DialogTitle>
          </DialogHeader>
          <StrategyForm 
            strategy={selectedStrategy} 
            onSubmit={handleUpdateStrategy} 
            onCancel={() => {
              setIsEditDialogOpen(false);
              setSelectedStrategy(null);
            }} 
          />
        </DialogContent>
      </Dialog>

      {/* Create Execution Dialog */}
      <Dialog open={isExecuteDialogOpen} onOpenChange={setIsExecuteDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>创建修复执行</DialogTitle>
          </DialogHeader>
          <ExecutionForm 
            strategies={strategies || []} 
            onSubmit={handleExecuteRepair} 
            onCancel={() => setIsExecuteDialogOpen(false)} 
          />
        </DialogContent>
      </Dialog>

      {/* Create Platform Dialog */}
      <Dialog open={isCreateDialogOpen && activeTab === 'platforms'} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>添加平台配置</DialogTitle>
          </DialogHeader>
          <PlatformForm onSubmit={handleCreatePlatform} onCancel={() => setIsCreateDialogOpen(false)} />
        </DialogContent>
      </Dialog>

      {/* Create Template Dialog */}
      <Dialog open={isCreateDialogOpen && activeTab === 'templates'} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>创建修复模板</DialogTitle>
          </DialogHeader>
          <TemplateForm onSubmit={handleCreateTemplate} onCancel={() => setIsCreateDialogOpen(false)} />
        </DialogContent>
      </Dialog>

      {/* Edit Template Dialog */}
      <Dialog open={isEditDialogOpen && activeTab === 'templates'} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>编辑修复模板</DialogTitle>
          </DialogHeader>
          <TemplateForm 
            template={selectedTemplate} 
            onSubmit={handleUpdateTemplate} 
            onCancel={() => {
              setIsEditDialogOpen(false);
              setSelectedTemplate(null);
            }} 
          />
        </DialogContent>
      </Dialog>

      {/* Cross-Platform Repair Dialog */}
      <Dialog open={isCrossPlatformDialogOpen} onOpenChange={setIsCrossPlatformDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>跨平台修复</DialogTitle>
          </DialogHeader>
          <CrossPlatformForm 
            strategies={strategies || []}
            platforms={platforms || []}
            onSubmit={handleCrossPlatformRepair} 
            onCancel={() => setIsCrossPlatformDialogOpen(false)} 
          />
        </DialogContent>
      </Dialog>

      {/* Execution Detail Dialog */}
      <Dialog open={!!selectedExecution} onOpenChange={() => setSelectedExecution(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>执行详情</DialogTitle>
          </DialogHeader>
          {selectedExecution && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm text-gray-500">执行ID</Label>
                  <p className="font-mono text-sm">{selectedExecution.id}</p>
                </div>
                <div>
                  <Label className="text-sm text-gray-500">策略</Label>
                  <p>{selectedExecution.strategy_name}</p>
                </div>
                <div>
                  <Label className="text-sm text-gray-500">目标资源</Label>
                  <p>{selectedExecution.target_resource}</p>
                </div>
                <div>
                  <Label className="text-sm text-gray-500">状态</Label>
                  <Badge className={getStatusColor(selectedExecution.status)}>
                    {selectedExecution.status}
                  </Badge>
                </div>
                <div>
                  <Label className="text-sm text-gray-500">请求者</Label>
                  <p>{selectedExecution.requested_by}</p>
                </div>
                <div>
                  <Label className="text-sm text-gray-500">创建时间</Label>
                  <p className="text-sm">{new Date(selectedExecution.created_at).toLocaleString()}</p>
                </div>
              </div>
              {selectedExecution.reason && (
                <div>
                  <Label className="text-sm text-gray-500">原因</Label>
                  <p className="text-sm">{selectedExecution.reason}</p>
                </div>
              )}
              {selectedExecution.parameters && Object.keys(selectedExecution.parameters).length > 0 && (
                <div>
                  <Label className="text-sm text-gray-500">参数</Label>
                  <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-auto">
                    {JSON.stringify(selectedExecution.parameters, null, 2)}
                  </pre>
                </div>
              )}
              {selectedExecution.result && (
                <div>
                  <Label className="text-sm text-gray-500">执行结果</Label>
                  <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-auto">
                    {JSON.stringify(selectedExecution.result, null, 2)}
                  </pre>
                </div>
              )}
              {selectedExecution.error_message && (
                <div>
                  <Label className="text-sm text-gray-500">错误信息</Label>
                  <p className="text-sm text-red-600">{selectedExecution.error_message}</p>
                </div>
              )}
              {selectedExecution.results && selectedExecution.results.length > 0 && (
                <div>
                  <Label className="text-sm text-gray-500">跨平台结果</Label>
                  <div className="space-y-2 mt-2">
                    {selectedExecution.results.map((result, idx) => (
                      <div key={idx} className="p-2 bg-gray-50 rounded">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{result.platform}</span>
                          <Badge className={getStatusColor(result.status)}>
                            {result.status}
                          </Badge>
                        </div>
                        {result.error && (
                          <p className="text-sm text-red-600 mt-1">{result.error}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================
// Form Components
// ============================================================

interface StrategyFormProps {
  strategy?: RepairStrategy | null;
  onSubmit: (data: Partial<RepairStrategy>) => void;
  onCancel: () => void;
}

function StrategyForm({ strategy, onSubmit, onCancel }: StrategyFormProps) {
  const [formData, setFormData] = useState<Partial<RepairStrategy>>(
    strategy || {
      name: '',
      description: '',
      repair_type: 'script',
      target_scope: '',
      platform: 'linux',
      priority: 'medium',
      auto_approve: false,
      status: 'active',
      script_content: '',
      config_changes: {},
      metadata: {},
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="name">策略名称 *</Label>
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
          <Label htmlFor="repair_type">修复类型</Label>
          <Select
            value={formData.repair_type}
            onValueChange={(value) => setFormData({ ...formData, repair_type: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="script">脚本</SelectItem>
              <SelectItem value="configuration">配置</SelectItem>
              <SelectItem value="restart">重启</SelectItem>
              <SelectItem value="rollback">回滚</SelectItem>
              <SelectItem value="custom">自定义</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="platform">平台</Label>
          <Select
            value={formData.platform}
            onValueChange={(value) => setFormData({ ...formData, platform: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="linux">Linux</SelectItem>
              <SelectItem value="windows">Windows</SelectItem>
              <SelectItem value="docker">Docker</SelectItem>
              <SelectItem value="kubernetes">Kubernetes</SelectItem>
              <SelectItem value="cloud">Cloud</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div>
        <Label htmlFor="target_scope">目标范围 *</Label>
        <Input
          id="target_scope"
          value={formData.target_scope}
          onChange={(e) => setFormData({ ...formData, target_scope: e.target.value })}
          required
          placeholder="例如: service, host, cluster"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="priority">优先级</Label>
          <Select
            value={formData.priority}
            onValueChange={(value) => setFormData({ ...formData, priority: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low">低</SelectItem>
              <SelectItem value="medium">中</SelectItem>
              <SelectItem value="high">高</SelectItem>
              <SelectItem value="critical">严重</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="status">状态</Label>
          <Select
            value={formData.status}
            onValueChange={(value) => setFormData({ ...formData, status: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="active">活跃</SelectItem>
              <SelectItem value="inactive">非活跃</SelectItem>
              <SelectItem value="deprecated">已弃用</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      {formData.repair_type === 'script' && (
        <div>
          <Label htmlFor="script_content">脚本内容</Label>
          <Textarea
            id="script_content"
            value={formData.script_content}
            onChange={(e) => setFormData({ ...formData, script_content: e.target.value })}
            rows={6}
            placeholder="输入修复脚本内容..."
          />
        </div>
      )}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="auto_approve"
          checked={formData.auto_approve}
          onChange={(e) => setFormData({ ...formData, auto_approve: e.target.checked })}
        />
        <Label htmlFor="auto_approve">自动批准执行</Label>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit">
          {strategy ? '更新' : '创建'}
        </Button>
      </DialogFooter>
    </form>
  );
}

interface ExecutionFormProps {
  strategies: RepairStrategy[];
  onSubmit: (strategyId: string, targetResource: string) => void;
  onCancel: () => void;
}

function ExecutionForm({ strategies, onSubmit, onCancel }: ExecutionFormProps) {
  const [strategyId, setStrategyId] = useState('');
  const [targetResource, setTargetResource] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(strategyId, targetResource);
  };

  const activeStrategies = strategies.filter(s => s.status === 'active');

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="strategy">修复策略 *</Label>
        <Select value={strategyId} onValueChange={setStrategyId}>
          <SelectTrigger>
            <SelectValue placeholder="选择修复策略" />
          </SelectTrigger>
          <SelectContent>
            {activeStrategies.map((strategy) => (
              <SelectItem key={strategy.id} value={strategy.id}>
                {strategy.name} ({strategy.platform})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label htmlFor="target_resource">目标资源 *</Label>
        <Input
          id="target_resource"
          value={targetResource}
          onChange={(e) => setTargetResource(e.target.value)}
          required
          placeholder="例如: hostname, service-name, pod-name"
        />
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit" disabled={!strategyId || !targetResource}>
          执行
        </Button>
      </DialogFooter>
    </form>
  );
}

interface PlatformFormProps {
  onSubmit: (data: Partial<Platform>) => void;
  onCancel: () => void;
}

function PlatformForm({ onSubmit, onCancel }: PlatformFormProps) {
  const [formData, setFormData] = useState<Partial<Platform>>({
    name: '',
    type: 'linux',
    endpoint: '',
    capabilities: [],
    metadata: {},
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="name">平台名称 *</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          required
        />
      </div>
      <div>
        <Label htmlFor="type">平台类型 *</Label>
        <Select
          value={formData.type}
          onValueChange={(value) => setFormData({ ...formData, type: value })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="linux">Linux</SelectItem>
            <SelectItem value="windows">Windows</SelectItem>
            <SelectItem value="docker">Docker</SelectItem>
            <SelectItem value="kubernetes">Kubernetes</SelectItem>
            <SelectItem value="cloud">Cloud</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label htmlFor="endpoint">端点URL</Label>
        <Input
          id="endpoint"
          value={formData.endpoint}
          onChange={(e) => setFormData({ ...formData, endpoint: e.target.value })}
          placeholder="例如: https://api.example.com"
        />
      </div>
      <div>
        <Label htmlFor="capabilities">能力 (逗号分隔)</Label>
        <Input
          id="capabilities"
          value={formData.capabilities?.join(', ')}
          onChange={(e) => setFormData({ 
            ...formData, 
            capabilities: e.target.value.split(',').map(c => c.trim()).filter(c => c) 
          })}
          placeholder="例如: script, service, process"
        />
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit">
          添加
        </Button>
      </DialogFooter>
    </form>
  );
}

interface TemplateFormProps {
  template?: RepairTemplate | null;
  onSubmit: (data: Partial<RepairTemplate>) => void;
  onCancel: () => void;
}

function TemplateForm({ template, onSubmit, onCancel }: TemplateFormProps) {
  const [formData, setFormData] = useState<Partial<RepairTemplate>>(
    template || {
      name: '',
      description: '',
      repair_type: 'script',
      platform: 'linux',
      template_content: '',
      parameters: [],
      category: 'general',
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
        <Label htmlFor="name">模板名称 *</Label>
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
          <Label htmlFor="repair_type">修复类型</Label>
          <Select
            value={formData.repair_type}
            onValueChange={(value) => setFormData({ ...formData, repair_type: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="script">脚本</SelectItem>
              <SelectItem value="configuration">配置</SelectItem>
              <SelectItem value="restart">重启</SelectItem>
              <SelectItem value="rollback">回滚</SelectItem>
              <SelectItem value="custom">自定义</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="platform">平台</Label>
          <Select
            value={formData.platform}
            onValueChange={(value) => setFormData({ ...formData, platform: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="linux">Linux</SelectItem>
              <SelectItem value="windows">Windows</SelectItem>
              <SelectItem value="docker">Docker</SelectItem>
              <SelectItem value="kubernetes">Kubernetes</SelectItem>
              <SelectItem value="cloud">Cloud</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div>
        <Label htmlFor="category">分类</Label>
        <Input
          id="category"
          value={formData.category}
          onChange={(e) => setFormData({ ...formData, category: e.target.value })}
          placeholder="例如: general, network, storage"
        />
      </div>
      <div>
        <Label htmlFor="template_content">模板内容 *</Label>
        <Textarea
          id="template_content"
          value={formData.template_content}
          onChange={(e) => setFormData({ ...formData, template_content: e.target.value })}
          rows={6}
          required
          placeholder="输入修复模板内容..."
        />
      </div>
      <div>
        <Label htmlFor="status">状态</Label>
        <Select
          value={formData.status}
          onValueChange={(value) => setFormData({ ...formData, status: value })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="active">活跃</SelectItem>
            <SelectItem value="inactive">非活跃</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit">
          {template ? '更新' : '创建'}
        </Button>
      </DialogFooter>
    </form>
  );
}

interface CrossPlatformFormProps {
  strategies: RepairStrategy[];
  platforms: Platform[];
  onSubmit: (data: { target_platforms: string[]; strategy_id: string; target_resources: Record<string, string>; parameters?: Record<string, any>; parallel?: boolean }) => void;
  onCancel: () => void;
}

function CrossPlatformForm({ strategies, platforms, onSubmit, onCancel }: CrossPlatformFormProps) {
  const [strategyId, setStrategyId] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [targetResources, setTargetResources] = useState<Record<string, string>>({});
  const [parallel, setParallel] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      target_platforms: selectedPlatforms,
      strategy_id: strategyId,
      target_resources: targetResources,
      parallel,
    });
  };

  const activeStrategies = strategies.filter(s => s.status === 'active');

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="strategy">修复策略 *</Label>
        <Select value={strategyId} onValueChange={setStrategyId}>
          <SelectTrigger>
            <SelectValue placeholder="选择修复策略" />
          </SelectTrigger>
          <SelectContent>
            {activeStrategies.map((strategy) => (
              <SelectItem key={strategy.id} value={strategy.id}>
                {strategy.name} ({strategy.platform})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label>目标平台 *</Label>
        <div className="space-y-2 mt-2">
          {platforms.map((platform) => (
            <div key={platform.id} className="flex items-center gap-2">
              <input
                type="checkbox"
                id={`platform-${platform.id}`}
                checked={selectedPlatforms.includes(platform.type)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedPlatforms([...selectedPlatforms, platform.type]);
                  } else {
                    setSelectedPlatforms(selectedPlatforms.filter(p => p !== platform.type));
                  }
                }}
              />
              <Label htmlFor={`platform-${platform.id}`} className="flex items-center gap-2">
                {getPlatformIcon(platform.type)}
                {platform.name}
              </Label>
            </div>
          ))}
        </div>
      </div>
      {selectedPlatforms.length > 0 && (
        <div>
          <Label>目标资源 *</Label>
          <div className="space-y-2 mt-2">
            {selectedPlatforms.map((platform) => (
              <div key={platform}>
                <Label htmlFor={`resource-${platform}`} className="text-sm">{platform}</Label>
                <Input
                  id={`resource-${platform}`}
                  value={targetResources[platform] || ''}
                  onChange={(e) => setTargetResources({ 
                    ...targetResources, 
                    [platform]: e.target.value 
                  })}
                  placeholder={`输入 ${platform} 的目标资源`}
                />
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="parallel"
          checked={parallel}
          onChange={(e) => setParallel(e.target.checked)}
        />
        <Label htmlFor="parallel">并行执行</Label>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit" disabled={!strategyId || selectedPlatforms.length === 0}>
          执行
        </Button>
      </DialogFooter>
    </form>
  );
}
