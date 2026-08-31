'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Zap, Play, Pause, Trash2, Settings, RefreshCw, Plus, AlertTriangle, Shield, Activity, FileText } from 'lucide-react';

interface ChaosExperiment {
  id: string;
  name: string;
  description: string;
  experiment_type: string;
  parameters: Record<string, any>;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'aborted';
  tags: string[];
  created_at: string;
  started_at?: string;
  completed_at?: string;
  results?: Record<string, any>;
}

interface ChaosScenario {
  id: string;
  name: string;
  description: string;
  fault_types: string[];
  target_services: string[];
  duration: number;
  rollback_plan: string;
  status: 'active' | 'inactive' | 'archived';
  created_at: string;
}

interface ChaosFault {
  id: string;
  name: string;
  fault_type: 'network_latency' | 'disk_failure' | 'cpu_overload' | 'memory_leak' | 'service_crash' | 'database_error' | 'cache_failure' | 'network_partition';
  description: string;
  parameters: Record<string, any>;
  severity: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
}

export default function ChaosAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'experiments' | 'scenarios' | 'faults'>('experiments');
  const [selectedExperiment, setSelectedExperiment] = useState<ChaosExperiment | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [newExperimentData, setNewExperimentData] = useState({
    name: '',
    description: '',
    experiment_type: 'latency_injection',
    parameters: {},
    severity: 'medium' as const,
    tags: [],
  });

  const debouncedSearch = useDebounce(searchTerm, 300);
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch chaos experiments
  const { data: chaosExperiments, isLoading: experimentsLoading, error: experimentsError, refetch: refetchExperiments } = useQuery<ChaosExperiment[]>({
    queryKey: ['chaos-experiments'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/chaos/experiments');
      return resp.data.experiments || resp.data || [];
    },
    refetchInterval: 30000,
  });

  // Fetch chaos scenarios
  const { data: chaosScenarios, isLoading: scenariosLoading, error: scenariosError, refetch: refetchScenarios } = useQuery<ChaosScenario[]>({
    queryKey: ['chaos-scenarios'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/chaos/scenarios');
      return resp.data.scenarios || resp.data || [];
    },
    refetchInterval: 60000,
  });

  // Fetch chaos faults
  const { data: chaosFaults, isLoading: faultsLoading, error: faultsError, refetch: refetchFaults } = useQuery<ChaosFault[]>({
    queryKey: ['chaos-faults'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/chaos/faults');
      return resp.data.faults || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Create experiment mutation
  const createExperimentMutation = useMutation({
    mutationFn: async (experimentData: typeof newExperimentData) => {
      const resp = await api.post('/api/v1/chaos/experiments', experimentData);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Experiment created successfully');
      setIsCreateDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ['chaos-experiments'] });
    },
    onError: (error: any) => {
      showError(`Failed to create experiment: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Start/Stop experiment mutation
  const toggleExperimentMutation = useMutation({
    mutationFn: async ({ experimentId, action }: { experimentId: string; action: 'start' | 'stop' | 'abort' }) => {
      const resp = await api.post(`/api/v1/chaos/experiments/${experimentId}/${action}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Experiment status updated');
      queryClient.invalidateQueries({ queryKey: ['chaos-experiments'] });
    },
    onError: (error: any) => {
      showError(`Failed to update experiment: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete experiment mutation
  const deleteExperimentMutation = useMutation({
    mutationFn: async (experimentId: string) => {
      const resp = await api.delete(`/api/v1/chaos/experiments/${experimentId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Experiment deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['chaos-experiments'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete experiment: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (experimentsError) {
      setPageError(experimentsError as Error);
      showError('Failed to load chaos experiments');
    }
  }, [experimentsError, setPageError, showError]);

  const filteredExperiments = chaosExperiments?.filter((exp) => {
    if (statusFilter !== 'all' && exp.status !== statusFilter) return false;
    if (severityFilter !== 'all' && exp.severity !== severityFilter) return false;
    if (debouncedSearch && !exp.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  }) || [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'aborted':
        return 'bg-orange-100 text-orange-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getFaultIcon = (faultType: string) => {
    switch (faultType) {
      case 'network_latency':
      case 'network_partition':
        return <Activity className="h-4 w-4" />;
      case 'disk_failure':
        return <Shield className="h-4 w-4" />;
      case 'cpu_overload':
        return <Zap className="h-4 w-4" />;
      case 'memory_leak':
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <Zap className="h-4 w-4" />;
    }
  };

  const handleCreateExperiment = () => {
    if (!newExperimentData.name) {
      showError('Please enter experiment name');
      return;
    }
    createExperimentMutation.mutate(newExperimentData);
  };

  const handleToggleExperiment = (experimentId: string, currentStatus: string) => {
    if (currentStatus === 'running') {
      toggleExperimentMutation.mutate({ experimentId, action: 'stop' });
    } else if (currentStatus === 'pending') {
      toggleExperimentMutation.mutate({ experimentId, action: 'start' });
    } else if (currentStatus === 'running') {
      toggleExperimentMutation.mutate({ experimentId, action: 'abort' });
    }
  };

  const handleDeleteExperiment = (experimentId: string) => {
    if (!window.confirm('Are you sure you want to delete this experiment?')) return;
    deleteExperimentMutation.mutate(experimentId);
  };

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
          description="无法加载混沌工程数据，请稍后重试"
          action={<Button onClick={() => refetchExperiments()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchExperiments()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Zap className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">混沌工程高级</h1>
            <p className="text-sm text-gray-500">混沌实验、场景和故障注入管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchExperiments()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            创建实验
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="experiments">
            <Activity className="h-4 w-4 mr-2" />
            混沌实验
          </TabsTrigger>
          <TabsTrigger value="scenarios">
            <Shield className="h-4 w-4 mr-2" />
            实验场景
          </TabsTrigger>
          <TabsTrigger value="faults">
            <Zap className="h-4 w-4 mr-2" />
            故障类型
          </TabsTrigger>
        </TabsList>

        <TabsContent value="experiments" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  混沌实验
                </span>
                <div className="flex gap-2">
                  <Input
                    placeholder="搜索实验..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                  <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                    <option value="all">全部状态</option>
                    <option value="pending">待处理</option>
                    <option value="running">运行中</option>
                    <option value="completed">已完成</option>
                    <option value="failed">失败</option>
                    <option value="aborted">已中止</option>
                  </Select>
                  <Select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
                    <option value="all">全部严重度</option>
                    <option value="low">低</option>
                    <option value="medium">中</option>
                    <option value="high">高</option>
                    <option value="critical">严重</option>
                  </Select>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {experimentsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : filteredExperiments.length === 0 ? (
                <EmptyState
                  title="没有混沌实验"
                  description="点击创建实验开始混沌工程测试"
                  action={<Button onClick={() => setIsCreateDialogOpen(true)}>创建实验</Button>}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>严重度</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>标签</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredExperiments.map((exp) => (
                      <TableRow key={exp.id}>
                        <TableCell className="font-mono text-sm">{exp.id}</TableCell>
                        <TableCell className="font-medium">{exp.name}</TableCell>
                        <TableCell className="capitalize">{exp.experiment_type.replace('_', ' ')}</TableCell>
                        <TableCell>
                          <Badge className={getSeverityColor(exp.severity)}>
                            {exp.severity}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(exp.status)}>
                            {exp.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1 flex-wrap">
                            {exp.tags.slice(0, 3).map((tag) => (
                              <Badge key={tag} variant="outline" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                            {exp.tags.length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{exp.tags.length - 3}
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(exp.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            {exp.status === 'pending' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleToggleExperiment(exp.id, exp.status)}
                              >
                                <Play className="h-4 w-4" />
                              </Button>
                            )}
                            {exp.status === 'running' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleToggleExperiment(exp.id, exp.status)}
                              >
                                <Pause className="h-4 w-4" />
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedExperiment(exp)}
                            >
                              <FileText className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteExperiment(exp.id)}
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

        <TabsContent value="scenarios" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                实验场景
              </CardTitle>
            </CardHeader>
            <CardContent>
              {scenariosLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !chaosScenarios || chaosScenarios.length === 0 ? (
                <EmptyState title="无实验场景" description="暂无实验场景记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead>故障类型</TableHead>
                      <TableHead>目标服务</TableHead>
                      <TableHead>持续时间(秒)</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {chaosScenarios.map((scenario) => (
                      <TableRow key={scenario.id}>
                        <TableCell className="font-mono text-sm">{scenario.id}</TableCell>
                        <TableCell className="font-medium">{scenario.name}</TableCell>
                        <TableCell>{scenario.description}</TableCell>
                        <TableCell>
                          <div className="flex gap-1 flex-wrap">
                            {scenario.fault_types.map((fault) => (
                              <Badge key={fault} variant="outline" className="text-xs">
                                {fault}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1 flex-wrap">
                            {scenario.target_services.map((service) => (
                              <Badge key={service} variant="outline" className="text-xs">
                                {service}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>{scenario.duration}</TableCell>
                        <TableCell>
                          <Badge className={scenario.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {scenario.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(scenario.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm">
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Play className="h-4 w-4" />
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

        <TabsContent value="faults" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                故障类型
              </CardTitle>
            </CardHeader>
            <CardContent>
              {faultsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !chaosFaults || chaosFaults.length === 0 ? (
                <EmptyState title="无故障类型" description="暂无故障类型记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>故障类型</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead>严重度</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {chaosFaults.map((fault) => (
                      <TableRow key={fault.id}>
                        <TableCell className="font-mono text-sm">{fault.id}</TableCell>
                        <TableCell className="font-medium">{fault.name}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getFaultIcon(fault.fault_type)}
                            <span className="capitalize">{fault.fault_type.replace('_', ' ')}</span>
                          </div>
                        </TableCell>
                        <TableCell>{fault.description}</TableCell>
                        <TableCell>
                          <Badge className={getSeverityColor(fault.severity)}>
                            {fault.severity}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(fault.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            <Settings className="h-4 w-4" />
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
      </Tabs>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建混沌实验</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">实验名称</label>
              <Input
                value={newExperimentData.name}
                onChange={(e) => setNewExperimentData({ ...newExperimentData, name: e.target.value })}
                placeholder="输入实验名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Input
                value={newExperimentData.description}
                onChange={(e) => setNewExperimentData({ ...newExperimentData, description: e.target.value })}
                placeholder="实验描述"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">实验类型</label>
              <Select
                value={newExperimentData.experiment_type}
                onChange={(e) => setNewExperimentData({ ...newExperimentData, experiment_type: e.target.value })}
              >
                <option value="latency_injection">延迟注入</option>
                <option value="fault_injection">故障注入</option>
                <option value="load_test">负载测试</option>
                <option value="stress_test">压力测试</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">严重度</label>
              <Select
                value={newExperimentData.severity}
                onChange={(e) => setNewExperimentData({ ...newExperimentData, severity: e.target.value as any })}
              >
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
                <option value="critical">严重</option>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateExperiment} disabled={createExperimentMutation.isPending}>
              {createExperimentMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
