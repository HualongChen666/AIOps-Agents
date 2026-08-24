'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Github, RefreshCw, TestTube, Settings, GitBranch, GitCommit } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface GitHubConfig {
  config_id: string;
  name: string;
  owner: string;
  repo: string;
  token: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
}

interface GitHubRepo {
  repo_id: string;
  name: string;
  owner: string;
  stars: number;
  forks: number;
  open_issues: number;
  updated_at: string;
}

interface GitHubCommit {
  sha: string;
  message: string;
  author: string;
  date: string;
}

export default function GitHubPage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    owner: '',
    repo: '',
    token: '',
    enabled: true,
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: GitHubConfig[] }>({
    queryKey: ['github-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/github/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: repoData, refetch: refetchRepos } = useQuery<{ repos: GitHubRepo[] }>({
    queryKey: ['github-repos'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/github/repos');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: commitData, refetch: refetchCommits } = useQuery<{ commits: GitHubCommit[] }>({
    queryKey: ['github-commits'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/github/commits');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/github/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['github-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', owner: '', repo: '', token: '', enabled: true });
      showSuccess('GitHub配置成功');
    },
    onError: () => {
      showError('GitHub配置失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/github/test/${id}`);
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
      showError('Failed to load GitHub data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const repos = repoData?.repos || [];
  const commits = commitData?.commits || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'owner' as const, label: '所有者' },
    { key: 'repo' as const, label: '仓库' },
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
          description="无法加载GitHub数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchRepos(); refetchCommits(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchRepos(); refetchCommits(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Github className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">GitHub集成</h1>
            <p className="text-sm text-gray-500">管理GitHub仓库集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchRepos(); refetchCommits(); }} variant="outline">
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
            <p className="text-sm text-gray-500 mt-1">GitHub配置</p>
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
            <CardTitle className="text-sm">仓库总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{repos.length}</p>
            <p className="text-sm text-gray-500 mt-1">已集成仓库</p>
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
              description="还没有配置GitHub集成"
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
            <GitBranch className="h-5 w-5" />
            仓库列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {repos.length === 0 ? (
            <EmptyState
              title="暂无仓库"
              description="还没有获取到GitHub仓库"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {repos.map((repo) => (
                <div key={repo.repo_id} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
                  <h3 className="font-medium mb-2">{repo.owner}/{repo.name}</h3>
                  <div className="grid grid-cols-3 gap-2 text-sm text-gray-600">
                    <div>
                      <span className="font-medium">⭐ {repo.stars}</span>
                    </div>
                    <div>
                      <span className="font-medium">🍴 {repo.forks}</span>
                    </div>
                    <div>
                      <span className="font-medium">🐛 {repo.open_issues}</span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    更新: {new Date(repo.updated_at).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitCommit className="h-5 w-5" />
            最新提交
          </CardTitle>
        </CardHeader>
        <CardContent>
          {commits.length === 0 ? (
            <EmptyState
              title="暂无提交"
              description="还没有获取到提交记录"
            />
          ) : (
            <div className="space-y-3">
              {commits.slice(0, 10).map((commit) => (
                <div key={commit.sha} className="p-4 border rounded-lg">
                  <p className="font-medium mb-2">{commit.message}</p>
                  <div className="text-sm text-gray-600">
                    <p>作者: {commit.author}</p>
                    <p>时间: {new Date(commit.date).toLocaleString()}</p>
                    <p className="font-mono text-xs mt-1">SHA: {commit.sha.substring(0, 7)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
