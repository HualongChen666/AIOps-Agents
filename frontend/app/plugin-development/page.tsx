'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { KpiCard } from '@/components/ui/KpiCard';
import { Code, RefreshCw, Play, Square, Plus, Trash2, Settings, FileText } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface PluginInfo {
  plugin_id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  plugin_type: string;
  status: string;
  dependencies: string[];
  registered_date: string;
}

interface SystemStatus {
  total_plugins: number;
  active_plugins: number;
  total_interfaces: number;
  enabled_plugins: number;
}

export default function PluginDevelopmentPage() {
  const [activeTab, setActiveTab] = useState<'plugins' | 'interfaces' | 'register' | 'test'>('plugins');
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [showInterfaceModal, setShowInterfaceModal] = useState(false);
  const [selectedPlugin, setSelectedPlugin] = useState<PluginInfo | null>(null);
  const [registerData, setRegisterData] = useState({
    plugin_id: '',
    name: '',
    version: '1.0.0',
    description: '',
    author: '',
    plugin_type: 'data_collector',
    dependencies: { dependencies: [] },
  });
  const [interfaceData, setInterfaceData] = useState({
    interface_id: '',
    interface_name: '',
    methods: [],
    events: [],
    configuration: {},
  });

  const queryClient = useQueryClient();

  // 🔧 获取系统状态
  const { data: statusData, isLoading: statusLoading, refetch: refetchStatus } = useQuery<{ data: SystemStatus; timestamp: string }>({
    queryKey: ['plugin-system-status'],
    queryFn: async () => {
      const resp = await api.get('/api/plugin-system/status');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 获取插件列表
  const { data: pluginsData, isLoading: pluginsLoading, refetch: refetchPlugins } = useQuery<{ data: { plugins: PluginInfo[]; count: number }; timestamp: string }>({
    queryKey: ['plugin-system-plugins'],
    queryFn: async () => {
      const resp = await api.get('/api/plugin-system/plugins');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 注册插件
  const registerPluginMutation = useMutation({
    mutationFn: async (data: typeof registerData) => {
      const resp = await api.post('/api/plugin-system/plugin/register', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugin-system-status'] });
      queryClient.invalidateQueries({ queryKey: ['plugin-system-plugins'] });
      setShowRegisterModal(false);
      showSuccess('插件注册成功');
    },
    onError: () => {
      showError('插件注册失败');
    },
  });

  // 🔧 启用插件
  const enablePluginMutation = useMutation({
    mutationFn: async (pluginId: string) => {
      const resp = await api.post(`/api/plugin-system/plugin/${pluginId}/enable`);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugin-system-plugins'] });
      showSuccess('插件已启用');
    },
    onError: () => {
      showError('插件启用失败');
    },
  });

  // 🔧 禁用插件
  const disablePluginMutation = useMutation({
    mutationFn: async (pluginId: string) => {
      const resp = await api.post(`/api/plugin-system/plugin/${pluginId}/disable`);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugin-system-plugins'] });
      showSuccess('插件已禁用');
    },
    onError: () => {
      showError('插件禁用失败');
    },
  });

  // 🔧 定义接口
  const defineInterfaceMutation = useMutation({
    mutationFn: async (data: typeof interfaceData) => {
      const resp = await api.post('/api/plugin-system/interface/define', data);
      return resp.data;
    },
    onSuccess: () => {
      setShowInterfaceModal(false);
      showSuccess('接口定义成功');
    },
    onError: () => {
      showError('接口定义失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(
    statusLoading || pluginsLoading
  );

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (pageError) {
      showError('Failed to load plugin development data');
      setPageError(pageError as Error);
    }
  }, [pageError, showError, setPageError]);

  const status = statusData?.data || { total_plugins: 0, active_plugins: 0, total_interfaces: 0, enabled_plugins: 0 };
  const plugins = pluginsData?.data?.plugins || [];

  const handleRegisterPlugin = () => {
    registerPluginMutation.mutate(registerData);
  };

  const handleEnablePlugin = (pluginId: string) => {
    enablePluginMutation.mutate(pluginId);
  };

  const handleDisablePlugin = (pluginId: string) => {
    disablePluginMutation.mutate(pluginId);
  };

  const handleDefineInterface = () => {
    defineInterfaceMutation.mutate(interfaceData);
  };

  const handleRefresh = () => {
    refetchStatus();
    refetchPlugins();
  };

  // 🔧 P1 Integration: Use enhanced loading and empty states
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
          description="无法加载插件开发数据，请稍后重试"
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Code className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">插件开发</h1>
            <p className="text-sm text-gray-500">插件系统管理和开发工具</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowRegisterModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            注册插件
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总插件数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{status.total_plugins}</p>
            <p className="text-sm text-gray-500 mt-1">系统插件总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃插件</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{status.active_plugins}</p>
            <p className="text-sm text-gray-500 mt-1">当前活跃插件</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已启用</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">{status.enabled_plugins}</p>
            <p className="text-sm text-gray-500 mt-1">已启用插件</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">接口数量</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{status.total_interfaces}</p>
            <p className="text-sm text-gray-500 mt-1">插件接口数量</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'plugins' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('plugins')}
        >
          <Code className="h-4 w-4 mr-2" />
          插件管理
        </Button>
        <Button
          variant={activeTab === 'interfaces' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('interfaces')}
        >
          <Settings className="h-4 w-4 mr-2" />
          接口定义
        </Button>
        <Button
          variant={activeTab === 'register' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('register')}
        >
          <Plus className="h-4 w-4 mr-2" />
          注册插件
        </Button>
        <Button
          variant={activeTab === 'test' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('test')}
        >
          <Play className="h-4 w-4 mr-2" />
          测试插件
        </Button>
      </div>

      {/* Plugins Tab */}
      {activeTab === 'plugins' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code className="h-5 w-5" />
              插件列表
            </CardTitle>
          </CardHeader>
          <CardContent>
            {plugins.length > 0 ? (
              <div className="space-y-4">
                {plugins.map((plugin) => (
                  <div key={plugin.plugin_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h3 className="font-semibold text-lg">{plugin.name}</h3>
                        <p className="text-sm text-gray-500">v{plugin.version} by {plugin.author}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={plugin.status as "error" | "success" | "warning" | "info" | "pending" | "unknown"} />
                        <span className="text-xs text-gray-500">{plugin.plugin_type}</span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 mb-3">{plugin.description}</p>
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-500">
                        注册: {new Date(plugin.registered_date).toLocaleDateString()}
                      </div>
                      <div className="flex gap-2">
                        {plugin.status === 'disabled' ? (
                          <Button size="sm" onClick={() => handleEnablePlugin(plugin.plugin_id)}>
                            <Play className="h-4 w-4 mr-1" />
                            启用
                          </Button>
                        ) : (
                          <Button size="sm" variant="outline" onClick={() => handleDisablePlugin(plugin.plugin_id)}>
                            <Square className="h-4 w-4 mr-1" />
                            禁用
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="暂无插件"
                description="插件系统暂无已注册插件"
                action={<Button onClick={() => setShowRegisterModal(true)}>注册第一个插件</Button>}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Interfaces Tab */}
      {activeTab === 'interfaces' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                接口定义
              </CardTitle>
              <Button size="sm" onClick={() => setShowInterfaceModal(true)}>
                <Plus className="h-4 w-4 mr-1" />
                定义接口
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="接口定义"
              description="定义插件接口规范和方法"
              action={<Button onClick={() => setShowInterfaceModal(true)}>定义第一个接口</Button>}
            />
          </CardContent>
        </Card>
      )}

      {/* Register Tab */}
      {activeTab === 'register' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              注册插件
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="注册插件"
              description="将新插件注册到插件系统"
              action={<Button onClick={() => setShowRegisterModal(true)}>开始注册</Button>}
            />
          </CardContent>
        </Card>
      )}

      {/* Test Tab */}
      {activeTab === 'test' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              测试插件
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="测试插件"
              description="测试插件功能和性能"
            />
          </CardContent>
        </Card>
      )}

      {/* Register Plugin Modal */}
      <EnhancedModal
        open={showRegisterModal}
        onOpenChange={setShowRegisterModal}
        title="注册插件"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">插件ID</label>
            <input
              type="text"
              value={registerData.plugin_id}
              onChange={(e) => setRegisterData({ ...registerData, plugin_id: e.target.value })}
              placeholder="输入唯一插件ID"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">插件名称</label>
            <input
              type="text"
              value={registerData.name}
              onChange={(e) => setRegisterData({ ...registerData, name: e.target.value })}
              placeholder="输入插件名称"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">版本</label>
            <input
              type="text"
              value={registerData.version}
              onChange={(e) => setRegisterData({ ...registerData, version: e.target.value })}
              placeholder="输入版本号 (如 1.0.0)"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">作者</label>
            <input
              type="text"
              value={registerData.author}
              onChange={(e) => setRegisterData({ ...registerData, author: e.target.value })}
              placeholder="输入作者名称"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">插件类型</label>
            <select
              value={registerData.plugin_type}
              onChange={(e) => setRegisterData({ ...registerData, plugin_type: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="data_collector">数据采集器</option>
              <option value="analyzer">分析器</option>
              <option value="notifier">通知器</option>
              <option value="action">动作执行器</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea
              value={registerData.description}
              onChange={(e) => setRegisterData({ ...registerData, description: e.target.value })}
              placeholder="输入插件描述"
              className="w-full px-3 py-2 border rounded-md bg-white min-h-[100px]"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowRegisterModal(false)}>
              取消
            </Button>
            <Button onClick={handleRegisterPlugin} disabled={registerPluginMutation.isPending}>
              {registerPluginMutation.isPending ? '注册中...' : '注册'}
            </Button>
          </div>
        </div>
      </EnhancedModal>

      {/* Define Interface Modal */}
      <EnhancedModal
        open={showInterfaceModal}
        onOpenChange={setShowInterfaceModal}
        title="定义接口"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">接口ID</label>
            <input
              type="text"
              value={interfaceData.interface_id}
              onChange={(e) => setInterfaceData({ ...interfaceData, interface_id: e.target.value })}
              placeholder="输入接口ID"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">接口名称</label>
            <input
              type="text"
              value={interfaceData.interface_name}
              onChange={(e) => setInterfaceData({ ...interfaceData, interface_name: e.target.value })}
              placeholder="输入接口名称"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowInterfaceModal(false)}>
              取消
            </Button>
            <Button onClick={handleDefineInterface} disabled={defineInterfaceMutation.isPending}>
              {defineInterfaceMutation.isPending ? '定义中...' : '定义'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}