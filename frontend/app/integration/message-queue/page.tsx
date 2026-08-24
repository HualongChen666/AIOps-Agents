'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Layers, RefreshCw, TestTube, Settings, Send } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface MQConfig {
  config_id: string;
  name: string;
  mq_type: 'rabbitmq' | 'activemq' | 'redis' | 'sqs';
  host: string;
  port: number;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
  queue_count: number;
}

interface MQQueue {
  queue_name: string;
  message_count: number;
  consumer_count: number;
  type: string;
}

interface MQMessage {
  queue: string;
  message_id: string;
  payload: string;
  timestamp: string;
}

export default function MessageQueuePage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    mq_type: 'rabbitmq' as const,
    host: '',
    port: 5672,
    enabled: true,
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: MQConfig[] }>({
    queryKey: ['mq-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/message-queue/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: queueData, refetch: refetchQueues } = useQuery<{ queues: MQQueue[] }>({
    queryKey: ['mq-queues'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/message-queue/queues');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: messageData, refetch: refetchMessages } = useQuery<{ messages: MQMessage[] }>({
    queryKey: ['mq-messages'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/message-queue/messages');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/message-queue/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mq-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', mq_type: 'rabbitmq', host: '', port: 5672, enabled: true });
      showSuccess('消息队列配置成功');
    },
    onError: () => {
      showError('消息队列配置失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/message-queue/test/${id}`);
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
      showError('Failed to load message queue data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const queues = queueData?.queues || [];
  const messages = messageData?.messages || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'mq_type' as const, label: '类型' },
    { key: 'host' as const, label: '主机' },
    { key: 'port' as const, label: '端口' },
    { key: 'status' as const, label: '状态', render: (value: string) => (
      <StatusBadge 
        status={value === 'connected' ? 'success' : value === 'error' ? 'error' : 'warning'} 
        text={value} 
      />
    )},
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
    { key: 'queue_count' as const, label: '队列数' },
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
          description="无法加载消息队列数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchQueues(); refetchMessages(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchQueues(); refetchMessages(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Layers className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">消息队列集成</h1>
            <p className="text-sm text-gray-500">管理RabbitMQ、ActiveMQ、Redis、SQS等消息队列</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchQueues(); refetchMessages(); }} variant="outline">
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
            <p className="text-sm text-gray-500 mt-1">MQ配置</p>
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
            <CardTitle className="text-sm">队列总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{queues.length}</p>
            <p className="text-sm text-gray-500 mt-1">消息队列</p>
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
              description="还没有配置消息队列集成"
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
            <Layers className="h-5 w-5" />
            队列列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {queues.length === 0 ? (
            <EmptyState
              title="暂无队列"
              description="还没有获取到消息队列"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {queues.map((queue) => (
                <div key={queue.queue_name} className="p-4 border rounded-lg">
                  <h3 className="font-medium mb-2">{queue.queue_name}</h3>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>消息数: {queue.message_count}</p>
                    <p>消费者数: {queue.consumer_count}</p>
                    <p>类型: {queue.type}</p>
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
            <Send className="h-5 w-5" />
            最新消息
          </CardTitle>
        </CardHeader>
        <CardContent>
          {messages.length === 0 ? (
            <EmptyState
              title="暂无消息"
              description="还没有获取到消息数据"
            />
          ) : (
            <div className="space-y-2">
              {messages.slice(0, 10).map((msg, index) => (
                <div key={index} className="p-3 border rounded hover:bg-gray-50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium">{msg.queue}</span>
                    <span className="text-sm text-gray-500">
                      {new Date(msg.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">ID: {msg.message_id}</p>
                  <p className="text-sm text-gray-700 truncate">{msg.payload}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
