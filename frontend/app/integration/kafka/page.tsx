'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { MessageSquare, RefreshCw, TestTube, Settings, Send } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface KafkaConfig {
  config_id: string;
  name: string;
  bootstrap_servers: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
  topic_count: number;
}

interface KafkaTopic {
  topic_name: string;
  partitions: number;
  replication_factor: number;
  message_count: number;
}

interface KafkaMessage {
  topic: string;
  partition: number;
  offset: number;
  key: string;
  value: string;
  timestamp: string;
}

export default function KafkaPage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showMessageModal, setShowMessageModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    bootstrap_servers: '',
    enabled: true,
  });
  const [messageFormData, setMessageFormData] = useState({
    topic: '',
    key: '',
    value: '',
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: KafkaConfig[] }>({
    queryKey: ['kafka-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/kafka/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: topicData, refetch: refetchTopics } = useQuery<{ topics: KafkaTopic[] }>({
    queryKey: ['kafka-topics'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/kafka/topics');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: messageData, refetch: refetchMessages } = useQuery<{ messages: KafkaMessage[] }>({
    queryKey: ['kafka-messages'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/kafka/messages');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/kafka/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kafka-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', bootstrap_servers: '', enabled: true });
      showSuccess('Kafka配置成功');
    },
    onError: () => {
      showError('Kafka配置失败');
    },
  });

  const sendMutation = useMutation({
    mutationFn: async (data: typeof messageFormData) => {
      const resp = await api.post('/api/v1/integration/kafka/send', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kafka-messages'] });
      setShowMessageModal(false);
      setMessageFormData({ topic: '', key: '', value: '' });
      showSuccess('消息发送成功');
    },
    onError: () => {
      showError('消息发送失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/kafka/test/${id}`);
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
      showError('Failed to load Kafka data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const topics = topicData?.topics || [];
  const messages = messageData?.messages || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'bootstrap_servers' as const, label: 'Bootstrap Servers' },
    {
      key: 'status' as const, label: '状态', render: (value: string) => (
        <StatusBadge
          status={value === 'connected' ? 'success' : value === 'error' ? 'error' : 'warning'}
          text={value}
        />
      )
    },
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
    { key: 'topic_count' as const, label: '主题数' },
    {
      key: 'last_sync' as const, label: '最后同步', render: (value: string | null) =>
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
          description="无法加载Kafka数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchTopics(); refetchMessages(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchTopics(); refetchMessages(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MessageSquare className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Kafka集成</h1>
            <p className="text-sm text-gray-500">管理Kafka消息队列集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchTopics(); refetchMessages(); }} variant="outline">
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
            <p className="text-sm text-gray-500 mt-1">Kafka配置</p>
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
            <CardTitle className="text-sm">主题总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{topics.length}</p>
            <p className="text-sm text-gray-500 mt-1">Kafka主题</p>
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
              description="还没有配置Kafka集成"
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
            <MessageSquare className="h-5 w-5" />
            主题列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {topics.length === 0 ? (
            <EmptyState
              title="暂无主题"
              description="还没有获取到Kafka主题"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {topics.map((topic) => (
                <div key={topic.topic_name} className="p-4 border rounded-lg">
                  <h3 className="font-medium mb-2">{topic.topic_name}</h3>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>分区数: {topic.partitions}</p>
                    <p>副本因子: {topic.replication_factor}</p>
                    <p>消息数: {topic.message_count}</p>
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
                    <span className="font-medium">{msg.topic}</span>
                    <span className="text-sm text-gray-500">
                      {new Date(msg.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">Key: {msg.key || '-'}</p>
                  <p className="text-sm text-gray-700">Value: {msg.value}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
