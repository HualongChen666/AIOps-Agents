'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Users, RefreshCw, TestTube, Settings, Send } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface TeamsConfig {
  config_id: string;
  name: string;
  tenant_id: string;
  client_id: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
  team_count: number;
}

interface TeamsTeam {
  team_id: string;
  name: string;
  description: string;
  member_count: number;
}

interface TeamsMessage {
  team: string;
  channel: string;
  message_id: string;
  content: string;
  sender: string;
  timestamp: string;
}

export default function TeamsPage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showMessageModal, setShowMessageModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    tenant_id: '',
    client_id: '',
    client_secret: '',
    enabled: true,
  });
  const [messageFormData, setMessageFormData] = useState({
    team: '',
    channel: '',
    content: '',
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: TeamsConfig[] }>({
    queryKey: ['teams-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/teams/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: teamData, refetch: refetchTeams } = useQuery<{ teams: TeamsTeam[] }>({
    queryKey: ['teams-teams'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/teams/teams');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: messageData, refetch: refetchMessages } = useQuery<{ messages: TeamsMessage[] }>({
    queryKey: ['teams-messages'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/teams/messages');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/teams/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', tenant_id: '', client_id: '', client_secret: '', enabled: true });
      showSuccess('Teams配置成功');
    },
    onError: () => {
      showError('Teams配置失败');
    },
  });

  const sendMutation = useMutation({
    mutationFn: async (data: typeof messageFormData) => {
      const resp = await api.post('/api/v1/integration/teams/send', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams-messages'] });
      setShowMessageModal(false);
      setMessageFormData({ team: '', channel: '', content: '' });
      showSuccess('消息发送成功');
    },
    onError: () => {
      showError('消息发送失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/teams/test/${id}`);
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
      showError('Failed to load Teams data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const teams = teamData?.teams || [];
  const messages = messageData?.messages || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'tenant_id' as const, label: '租户ID' },
    { key: 'client_id' as const, label: '客户端ID' },
    {
      key: 'status' as const, label: '状态', render: (value: string) => (
        <StatusBadge
          status={value === 'connected' ? 'success' : value === 'error' ? 'error' : 'warning'}
          text={value}
        />
      )
    },
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
    { key: 'team_count' as const, label: '团队数' },
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
          description="无法加载Teams数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchTeams(); refetchMessages(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchTeams(); refetchMessages(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Teams集成</h1>
            <p className="text-sm text-gray-500">管理Microsoft Teams协作集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchTeams(); refetchMessages(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowConfigModal(true)}>
            <Settings className="h-4 w-4 mr-2" />
            添加配置
          </Button>
          <Button onClick={() => setShowMessageModal(true)}>
            <Send className="h-4 w-4 mr-2" />
            发送消息
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
            <p className="text-sm text-gray-500 mt-1">Teams配置</p>
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
            <CardTitle className="text-sm">团队总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{teams.length}</p>
            <p className="text-sm text-gray-500 mt-1">Teams团队</p>
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
              description="还没有配置Teams集成"
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
            <Users className="h-5 w-5" />
            团队列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {teams.length === 0 ? (
            <EmptyState
              title="暂无团队"
              description="还没有获取到Teams团队"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {teams.map((team) => (
                <div key={team.team_id} className="p-4 border rounded-lg">
                  <h3 className="font-medium mb-2">{team.name}</h3>
                  <p className="text-sm text-gray-600 mb-2">{team.description}</p>
                  <p className="text-sm text-gray-600">成员数: {team.member_count}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            消息历史
          </CardTitle>
        </CardHeader>
        <CardContent>
          {messages.length === 0 ? (
            <EmptyState
              title="暂无消息"
              description="还没有获取到消息历史"
            />
          ) : (
            <div className="space-y-2">
              {messages.slice(0, 10).map((msg) => (
                <div key={msg.message_id} className="p-3 border rounded hover:bg-gray-50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium">{msg.team} / {msg.channel}</span>
                    <span className="text-sm text-gray-500">
                      {new Date(msg.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">{msg.content}</p>
                  <p className="text-xs text-gray-500 mt-1">发送者: {msg.sender}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
