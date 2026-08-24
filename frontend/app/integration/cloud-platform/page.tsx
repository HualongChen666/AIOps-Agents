'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Cloud, RefreshCw, TestTube, Settings, Server, Database, HardDrive } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface CloudConfig {
  config_id: string;
  name: string;
  provider: 'aws' | 'azure' | 'gcp' | 'alibaba';
  region: string;
  access_key: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
}

interface CloudInstance {
  instance_id: string;
  name: string;
  instance_type: string;
  state: string;
  public_ip: string;
  private_ip: string;
  launched_at: string;
}

interface CloudResource {
  resource_id: string;
  type: string;
  name: string;
  region: string;
  status: string;
  cost: number;
}

export default function CloudPlatformPage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'instances' | 'resources'>('instances');
  const [formData, setFormData] = useState({
    name: '',
    provider: 'aws' as const,
    region: '',
    access_key: '',
    secret_key: '',
    enabled: true,
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: CloudConfig[] }>({
    queryKey: ['cloud-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/cloud/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: instanceData, refetch: refetchInstances } = useQuery<{ instances: CloudInstance[] }>({
    queryKey: ['cloud-instances'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/cloud/instances');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: resourceData, refetch: refetchResources } = useQuery<{ resources: CloudResource[] }>({
    queryKey: ['cloud-resources'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/cloud/resources');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/cloud/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cloud-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', provider: 'aws', region: '', access_key: '', secret_key: '', enabled: true });
      showSuccess('云平台配置成功');
    },
    onError: () => {
      showError('云平台配置失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/cloud/test/${id}`);
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
      showError('Failed to load cloud platform data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const instances = instanceData?.instances || [];
  const resources = resourceData?.resources || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'provider' as const, label: '提供商' },
    { key: 'region' as const, label: '区域' },
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
          description="无法加载云平台数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchInstances(); refetchResources(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchInstances(); refetchResources(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Cloud className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">云平台集成</h1>
            <p className="text-sm text-gray-500">管理AWS、Azure、GCP、阿里云等云平台集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchInstances(); refetchResources(); }} variant="outline">
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
            <p className="text-sm text-gray-500 mt-1">云平台配置</p>
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
            <CardTitle className="text-sm">实例总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{instances.length}</p>
            <p className="text-sm text-gray-500 mt-1">云实例</p>
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
              description="还没有配置云平台集成"
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

      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'instances' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('instances')}
        >
          <Server className="h-4 w-4 mr-2" />
          实例管理
        </Button>
        <Button
          variant={activeTab === 'resources' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('resources')}
        >
          <Database className="h-4 w-4 mr-2" />
          资源管理
        </Button>
      </div>

      {activeTab === 'instances' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              实例列表
            </CardTitle>
          </CardHeader>
          <CardContent>
            {instances.length === 0 ? (
              <EmptyState
                title="暂无实例"
                description="还没有获取到云实例"
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {instances.map((instance) => (
                  <div key={instance.instance_id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-medium">{instance.name}</h3>
                      <span className={`px-2 py-1 rounded text-xs ${
                        instance.state === 'running' ? 'bg-green-100 text-green-800' :
                        instance.state === 'stopped' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {instance.state}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 space-y-1">
                      <p>类型: {instance.instance_type}</p>
                      <p>公网IP: {instance.public_ip || '-'}</p>
                      <p>私网IP: {instance.private_ip || '-'}</p>
                      <p>启动时间: {new Date(instance.launched_at).toLocaleString()}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'resources' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              资源列表
            </CardTitle>
          </CardHeader>
          <CardContent>
            {resources.length === 0 ? (
              <EmptyState
                title="暂无资源"
                description="还没有获取到云资源"
              />
            ) : (
              <div className="space-y-3">
                {resources.slice(0, 10).map((resource) => (
                  <div key={resource.resource_id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{resource.name}</span>
                      <div className="flex gap-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          resource.status === 'available' ? 'bg-green-100 text-green-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {resource.status}
                        </span>
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                          ${resource.cost}/月
                        </span>
                      </div>
                    </div>
                    <div className="text-sm text-gray-600">
                      <p>类型: {resource.type}</p>
                      <p>区域: {resource.region}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
