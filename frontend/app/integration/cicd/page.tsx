'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { GitBranch, RefreshCw, TestTube, Settings, PlayCircle, CheckCircle, XCircle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface CICDConfig {
  config_id: string;
  name: string;
  cicd_type: 'jenkins' | 'gitlab' | 'circleci' | 'github-actions';
  url: string;
  token: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
}

interface CICDPipeline {
  pipeline_id: string;
  name: string;
  project: string;
  status: 'success' | 'failed' | 'running' | 'pending';
  branch: string;
  last_run: string;
  duration: number;
}

interface CICDBuild {
  build_id: string;
  pipeline: string;
  number: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  triggered_by: string;
}

export default function CICDPage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    cicd_type: 'jenkins' as const,
    url: '',
    token: '',
    enabled: true,
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: CICDConfig[] }>({
    queryKey: ['cicd-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/cicd/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: pipelineData, refetch: refetchPipelines } = useQuery<{ pipelines: CICDPipeline[] }>({
    queryKey: ['cicd-pipelines'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/cicd/pipelines');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: buildData, refetch: refetchBuilds } = useQuery<{ builds: CICDBuild[] }>({
    queryKey: ['cicd-builds'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/cicd/builds');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/cicd/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cicd-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', cicd_type: 'jenkins', url: '', token: '', enabled: true });
      showSuccess('CI/CD配置成功');
    },
    onError: () => {
      showError('CI/CD配置失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/cicd/test/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('连接测试成功');
      refetchConfig();
    },
    onError: () => {
      showError('连接测试失败');
    },
  });

  useEffect(() => {
    if (error) {
      showError('Failed to load CI/CD data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const pipelines = pipelineData?.pipelines || [];
  const builds = buildData?.builds || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'cicd_type' as const, label: '类型' },
    { key: 'url' as const, label: 'URL' },
    { key: 'status' as const, label: '状态', render: (value: string) => (
      <StatusBadge 
        status={value === 'connected' ? 'success' : value === 'error' ? 'error' : 'warning'} 
        text={value} 
      />
    )},
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
    { key: 'last_sync' as const, label: '最后同步', render: (value: string | null) => 
      value ? new Date(value).toLocaleString() : '-' 
    },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载CI/CD数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchPipelines(); refetchBuilds(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchPipelines(); refetchBuilds(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GitBranch className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">CI/CD集成</h1>
            <p className="text-sm text-gray-500">管理Jenkins、GitLab CI、CircleCI等CI/CD集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchPipelines(); refetchBuilds(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowConfigModal(true)}>
            <Settings className="h-4 w-4 mr-2" />
            添加配置
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">配置数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{configs.length}</p>
            <p className="text-sm text-gray-500 mt-1">CI/CD配置</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃连接</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {configs.filter(c => c.status === 'connected').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">已连接</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">管道总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{pipelines.length}</p>
            <p className="text-sm text-gray-500 mt-1">CI/CD管道</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            配置列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {configs.length === 0 ? (
            <EmptyState
              title="暂无配置"
              description="还没有配置CI/CD集成"
              action={<Button onClick={() => setShowConfigModal(true)}>添加配置</Button>}
            />
          ) : (
            <DataTable
              data={configs}
              columns={configColumns}
              pageSize={10}
              emptyMessage="暂无配置"
              onRowClick={(config) => (
                <Button 
                  size="sm" 
                  onClick={() => testMutation.mutate(config.config_id)}
                  disabled={testMutation.isPending}
                >
                  <TestTube className="h-4 w-4 mr-1" />
                  测试连接
                </Button>
              )}
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PlayCircle className="h-5 w-5" />
            管道列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {pipelines.length === 0 ? (
            <EmptyState
              title="暂无管道"
              description="还没有获取到CI/CD管道"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {pipelines.map((pipeline) => (
                <div key={pipeline.pipeline_id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium">{pipeline.name}</h3>
                    <span className={`px-2 py-1 rounded text-xs ${
                      pipeline.status === 'success' ? 'bg-green-100 text-green-800' :
                      pipeline.status === 'failed' ? 'bg-red-100 text-red-800' :
                      pipeline.status === 'running' ? 'bg-blue-100 text-blue-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {pipeline.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>项目: {pipeline.project}</p>
                    <p>分支: {pipeline.branch}</p>
                    <p>持续时间: {pipeline.duration}s</p>
                    <p>最后运行: {new Date(pipeline.last_run).toLocaleString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            构建历史
          </CardTitle>
        </CardHeader>
        <CardContent>
          {builds.length === 0 ? (
            <EmptyState
              title="暂无构建"
              description="还没有获取到构建历史"
            />
          ) : (
            <div className="space-y-2">
              {builds.slice(0, 10).map((build) => (
                <div key={build.build_id} className="p-3 border rounded hover:bg-gray-50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium">{build.pipeline} #{build.number}</span>
                    <div className="flex items-center gap-2">
                      {build.status === 'success' && <CheckCircle className="h-4 w-4 text-green-600" />}
                      {build.status === 'failed' && <XCircle className="h-4 w-4 text-red-600" />}
                      {build.status === 'running' && <PlayCircle className="h-4 w-4 text-blue-600" />}
                      <span className="text-sm text-gray-500">
                        {new Date(build.started_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">触发者: {build.triggered_by}</p>
                  {build.completed_at && (
                    <p className="text-sm text-gray-600">
                      完成时间: {new Date(build.completed_at).toLocaleString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
