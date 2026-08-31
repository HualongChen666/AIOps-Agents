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
import { Brain, Cpu, FileText, GitBranch, Activity, TrendingUp, Play, Pause, Trash2, RefreshCw, Plus, Settings, Download, Upload } from 'lucide-react';

interface FineTuningJob {
  id: string;
  base_model: string;
  model_name: string;
  dataset_id: string;
  learning_rate: number;
  epochs: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  accuracy?: number;
  loss?: number;
}

interface Runbook {
  id: string;
  title: string;
  alert_type: string;
  content: string;
  created_at: string;
  author: string;
  status: 'draft' | 'published' | 'archived';
}

interface AnalysisReport {
  id: string;
  analysis_type: string;
  target: string;
  findings: string[];
  confidence: number;
  created_at: string;
  status: 'processing' | 'completed' | 'failed';
}

interface DSLDefinition {
  id: string;
  name: string;
  definition: string;
  version: string;
  created_at: string;
  status: 'active' | 'inactive';
}

export default function AIAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'finetuning' | 'runbooks' | 'analysis' | 'dsl'>('finetuning');
  const [selectedJob, setSelectedJob] = useState<FineTuningJob | null>(null);
  const [selectedRunbook, setSelectedRunbook] = useState<Runbook | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newJobData, setNewJobData] = useState({
    base_model: '',
    model_name: '',
    dataset_id: '',
    learning_rate: 0.0001,
    epochs: 3,
  });

  const debouncedSearch = useDebounce(searchTerm, 300);
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch fine-tuning jobs
  const { data: finetuningJobs, isLoading: jobsLoading, error: jobsError, refetch: refetchJobs } = useQuery<FineTuningJob[]>({
    queryKey: ['ai-finetuning-jobs'],
    queryFn: async () => {
      const resp = await api.get('/api/ai/fine-tuning/jobs');
      return resp.data.jobs || resp.data || [];
    },
    refetchInterval: 30000,
  });

  // Fetch runbooks
  const { data: runbooks, isLoading: runbooksLoading, error: runbooksError, refetch: refetchRunbooks } = useQuery<Runbook[]>({
    queryKey: ['ai-runbooks'],
    queryFn: async () => {
      const resp = await api.get('/api/ai/runbooks');
      return resp.data.runbooks || resp.data || [];
    },
    refetchInterval: 60000,
  });

  // Fetch analysis reports
  const { data: analysisReports, isLoading: analysisLoading, error: analysisError, refetch: refetchAnalysis } = useQuery<AnalysisReport[]>({
    queryKey: ['ai-analysis-reports'],
    queryFn: async () => {
      const resp = await api.get('/api/ai/analysis/reports');
      return resp.data.reports || resp.data || [];
    },
    refetchInterval: 60000,
  });

  // Fetch DSL definitions
  const { data: dslDefinitions, isLoading: dslLoading, error: dslError, refetch: refetchDSL } = useQuery<DSLDefinition[]>({
    queryKey: ['ai-dsl-definitions'],
    queryFn: async () => {
      const resp = await api.get('/api/ai/dsl/definitions');
      return resp.data.definitions || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Create fine-tuning job mutation
  const createJobMutation = useMutation({
    mutationFn: async (jobData: typeof newJobData) => {
      const resp = await api.post('/api/ai/fine-tuning/jobs', jobData);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Fine-tuning job created successfully');
      setIsCreateDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ['ai-finetuning-jobs'] });
    },
    onError: (error: any) => {
      showError(`Failed to create job: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Start/Stop job mutation
  const toggleJobMutation = useMutation({
    mutationFn: async ({ jobId, action }: { jobId: string; action: 'start' | 'stop' }) => {
      const resp = await api.post(`/api/ai/fine-tuning/jobs/${jobId}/${action}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Job status updated');
      queryClient.invalidateQueries({ queryKey: ['ai-finetuning-jobs'] });
    },
    onError: (error: any) => {
      showError(`Failed to update job: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete job mutation
  const deleteJobMutation = useMutation({
    mutationFn: async (jobId: string) => {
      const resp = await api.delete(`/api/ai/fine-tuning/jobs/${jobId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Job deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['ai-finetuning-jobs'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete job: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (jobsError) {
      setPageError(jobsError as Error);
      showError('Failed to load fine-tuning jobs');
    }
  }, [jobsError, setPageError, showError]);

  const filteredJobs = finetuningJobs?.filter((job) => {
    if (statusFilter !== 'all' && job.status !== statusFilter) return false;
    if (debouncedSearch && !job.model_name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
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
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleCreateJob = () => {
    if (!newJobData.base_model || !newJobData.model_name || !newJobData.dataset_id) {
      showError('Please fill in all required fields');
      return;
    }
    createJobMutation.mutate(newJobData);
  };

  const handleToggleJob = (jobId: string, currentStatus: string) => {
    const action = currentStatus === 'running' ? 'stop' : 'start';
    toggleJobMutation.mutate({ jobId, action });
  };

  const handleDeleteJob = (jobId: string) => {
    if (!window.confirm('Are you sure you want to delete this job?')) return;
    deleteJobMutation.mutate(jobId);
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
          description="无法加载AI高级分析数据，请稍后重试"
          action={<Button onClick={() => refetchJobs()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchJobs()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Brain className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">AI高级分析</h1>
            <p className="text-sm text-gray-500">模型微调、Runbook生成和智能分析</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchJobs()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            创建任务
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="finetuning">
            <Cpu className="h-4 w-4 mr-2" />
            模型微调
          </TabsTrigger>
          <TabsTrigger value="runbooks">
            <FileText className="h-4 w-4 mr-2" />
            Runbook
          </TabsTrigger>
          <TabsTrigger value="analysis">
            <Activity className="h-4 w-4 mr-2" />
            智能分析
          </TabsTrigger>
          <TabsTrigger value="dsl">
            <GitBranch className="h-4 w-4 mr-2" />
            DSL定义
          </TabsTrigger>
        </TabsList>

        <TabsContent value="finetuning" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Cpu className="h-5 w-5" />
                  模型微调任务
                </span>
                <div className="flex gap-2">
                  <Input
                    placeholder="搜索模型..."
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
                  </Select>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {jobsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : filteredJobs.length === 0 ? (
                <EmptyState
                  title="没有微调任务"
                  description="点击创建任务开始模型微调"
                  action={<Button onClick={() => setIsCreateDialogOpen(true)}>创建任务</Button>}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>模型名称</TableHead>
                      <TableHead>基础模型</TableHead>
                      <TableHead>数据集</TableHead>
                      <TableHead>学习率</TableHead>
                      <TableHead>轮数</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>准确率</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredJobs.map((job) => (
                      <TableRow key={job.id}>
                        <TableCell className="font-mono text-sm">{job.id}</TableCell>
                        <TableCell className="font-medium">{job.model_name}</TableCell>
                        <TableCell>{job.base_model}</TableCell>
                        <TableCell>{job.dataset_id}</TableCell>
                        <TableCell>{job.learning_rate}</TableCell>
                        <TableCell>{job.epochs}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(job.status)}>
                            {job.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{job.accuracy ? `${(job.accuracy * 100).toFixed(2)}%` : '-'}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(job.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleJob(job.id, job.status)}
                              disabled={job.status === 'completed' || job.status === 'failed'}
                            >
                              {job.status === 'running' ? (
                                <Pause className="h-4 w-4" />
                              ) : (
                                <Play className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteJob(job.id)}
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

        <TabsContent value="runbooks" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Runbook管理
              </CardTitle>
            </CardHeader>
            <CardContent>
              {runbooksLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !runbooks || runbooks.length === 0 ? (
                <EmptyState
                  title="没有Runbook"
                  description="暂无Runbook记录"
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>标题</TableHead>
                      <TableHead>告警类型</TableHead>
                      <TableHead>作者</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {runbooks.map((runbook) => (
                      <TableRow key={runbook.id}>
                        <TableCell className="font-mono text-sm">{runbook.id}</TableCell>
                        <TableCell className="font-medium">{runbook.title}</TableCell>
                        <TableCell>{runbook.alert_type}</TableCell>
                        <TableCell>{runbook.author}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(runbook.status)}>
                            {runbook.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(runbook.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedRunbook(runbook)}
                          >
                            查看详情
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

        <TabsContent value="analysis" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                智能分析报告
              </CardTitle>
            </CardHeader>
            <CardContent>
              {analysisLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !analysisReports || analysisReports.length === 0 ? (
                <EmptyState
                  title="没有分析报告"
                  description="暂无智能分析报告"
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>分析类型</TableHead>
                      <TableHead>目标</TableHead>
                      <TableHead>置信度</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {analysisReports.map((report) => (
                      <TableRow key={report.id}>
                        <TableCell className="font-mono text-sm">{report.id}</TableCell>
                        <TableCell>{report.analysis_type}</TableCell>
                        <TableCell>{report.target}</TableCell>
                        <TableCell>{(report.confidence * 100).toFixed(1)}%</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(report.status)}>
                            {report.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(report.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            查看详情
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

        <TabsContent value="dsl" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <GitBranch className="h-5 w-5" />
                  DSL定义
                </span>
                <Button size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  创建DSL
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dslLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !dslDefinitions || dslDefinitions.length === 0 ? (
                <EmptyState
                  title="没有DSL定义"
                  description="暂无DSL定义记录"
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>版本</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dslDefinitions.map((dsl) => (
                      <TableRow key={dsl.id}>
                        <TableCell className="font-mono text-sm">{dsl.id}</TableCell>
                        <TableCell className="font-medium">{dsl.name}</TableCell>
                        <TableCell>{dsl.version}</TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(dsl.status)}>
                            {dsl.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(dsl.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm">
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Download className="h-4 w-4" />
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

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建微调任务</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">基础模型</label>
              <Input
                value={newJobData.base_model}
                onChange={(e) => setNewJobData({ ...newJobData, base_model: e.target.value })}
                placeholder="例如: gpt-3.5-turbo"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
              <Input
                value={newJobData.model_name}
                onChange={(e) => setNewJobData({ ...newJobData, model_name: e.target.value })}
                placeholder="例如: my-custom-model"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">数据集ID</label>
              <Input
                value={newJobData.dataset_id}
                onChange={(e) => setNewJobData({ ...newJobData, dataset_id: e.target.value })}
                placeholder="数据集ID"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">学习率</label>
                <Input
                  type="number"
                  step="0.00001"
                  value={newJobData.learning_rate}
                  onChange={(e) => setNewJobData({ ...newJobData, learning_rate: parseFloat(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">训练轮数</label>
                <Input
                  type="number"
                  value={newJobData.epochs}
                  onChange={(e) => setNewJobData({ ...newJobData, epochs: parseInt(e.target.value) })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateJob} disabled={createJobMutation.isPending}>
              {createJobMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
