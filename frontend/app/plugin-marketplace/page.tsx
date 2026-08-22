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
import { Package, RefreshCw, Download, CheckCircle, XCircle, Star, Plus, Search } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface PluginListing {
  plugin_id: string;
  plugin_name: string;
  version: string;
  description: string;
  author: string;
  quality: string;
  review_status: string;
  downloads: number;
  rating: number;
  published_date: string;
}

interface MarketplaceStatus {
  total_plugins: number;
  published_plugins: number;
  pending_review: number;
  approved_plugins: number;
}

export default function PluginMarketplacePage() {
  const [activeTab, setActiveTab] = useState<'marketplace' | 'publish' | 'installed'>('marketplace');
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [showInstallModal, setShowInstallModal] = useState(false);
  const [selectedPlugin, setSelectedPlugin] = useState<PluginListing | null>(null);
  const [publishData, setPublishData] = useState({
    plugin_id: '',
    plugin_name: '',
    version: '1.0.0',
    description: '',
    author: '',
    plugin_code: '',
    plugin_config: {},
    quality: 'community',
  });
  const [searchQuery, setSearchQuery] = useState('');

  const queryClient = useQueryClient();

  // 🔧 获取市场状态
  const { data: statusData, isLoading: statusLoading, refetch: refetchStatus } = useQuery<{ data: MarketplaceStatus; timestamp: string }>({
    queryKey: ['plugin-marketplace-status'],
    queryFn: async () => {
      const resp = await api.get('/api/plugin-marketplace/status');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 获取插件列表
  const { data: listingsData, isLoading: listingsLoading, refetch: refetchListings } = useQuery<{ data: { listings: PluginListing[]; count: number }; timestamp: string }>({
    queryKey: ['plugin-marketplace-listings'],
    queryFn: async () => {
      const resp = await api.get('/api/plugin-marketplace/listings');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 发布插件
  const publishPluginMutation = useMutation({
    mutationFn: async (data: typeof publishData) => {
      const resp = await api.post('/api/plugin-marketplace/publish', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugin-marketplace-status'] });
      queryClient.invalidateQueries({ queryKey: ['plugin-marketplace-listings'] });
      setShowPublishModal(false);
      showSuccess('插件发布成功');
    },
    onError: () => {
      showError('插件发布失败');
    },
  });

  // 🔧 下载插件
  const downloadPluginMutation = useMutation({
    mutationFn: async (pluginId: string) => {
      const resp = await api.post(`/api/plugin-marketplace/plugin/${pluginId}/download`);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugin-marketplace-listings'] });
      showSuccess('插件下载成功');
    },
    onError: () => {
      showError('插件下载失败');
    },
  });

  // 🔧 批准插件
  const approvePluginMutation = useMutation({
    mutationFn: async ({ pluginId, reviewer }: { pluginId: string; reviewer: string }) => {
      const resp = await api.post(`/api/plugin-marketplace/plugin/${pluginId}/approve`, { reviewer });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugin-marketplace-listings'] });
      showSuccess('插件已批准');
    },
    onError: () => {
      showError('插件批准失败');
    },
  });

  // 🔧 拒绝插件
  const rejectPluginMutation = useMutation({
    mutationFn: async ({ pluginId, reason }: { pluginId: string; reason: string }) => {
      const resp = await api.post(`/api/plugin-marketplace/plugin/${pluginId}/reject`, { reason });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugin-marketplace-listings'] });
      showSuccess('插件已拒绝');
    },
    onError: () => {
      showError('插件拒绝失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(
    statusLoading || listingsLoading
  );

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (pageError) {
      showError('Failed to load plugin marketplace data');
      setPageError(pageError as Error);
    }
  }, [pageError, showError, setPageError]);

  const status = statusData?.data || { total_plugins: 0, published_plugins: 0, pending_review: 0, approved_plugins: 0 };
  const listings = listingsData?.data?.listings || [];
  const filteredListings = listings.filter(plugin =>
    plugin.plugin_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    plugin.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    plugin.author.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handlePublishPlugin = () => {
    publishPluginMutation.mutate(publishData);
  };

  const handleDownloadPlugin = (pluginId: string) => {
    downloadPluginMutation.mutate(pluginId);
  };

  const handleApprovePlugin = (pluginId: string) => {
    approvePluginMutation.mutate({ pluginId, reviewer: 'admin' });
  };

  const handleRejectPlugin = (pluginId: string) => {
    const reason = 'Quality issues';
    rejectPluginMutation.mutate({ pluginId, reason });
  };

  const handleRefresh = () => {
    refetchStatus();
    refetchListings();
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
          description="无法加载插件市场数据，请稍后重试"
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
          <Package className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">插件市场</h1>
            <p className="text-sm text-gray-500">发现、安装和管理插件</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowPublishModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            发布插件
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
            <p className="text-sm text-gray-500 mt-1">市场插件总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已发布</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{status.published_plugins}</p>
            <p className="text-sm text-gray-500 mt-1">已发布插件</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">待审核</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{status.pending_review}</p>
            <p className="text-sm text-gray-500 mt-1">待审核插件</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已批准</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">{status.approved_plugins}</p>
            <p className="text-sm text-gray-500 mt-1">已批准插件</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'marketplace' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('marketplace')}
        >
          <Package className="h-4 w-4 mr-2" />
          插件市场
        </Button>
        <Button
          variant={activeTab === 'publish' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('publish')}
        >
          <Plus className="h-4 w-4 mr-2" />
          发布插件
        </Button>
        <Button
          variant={activeTab === 'installed' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('installed')}
        >
          <CheckCircle className="h-4 w-4 mr-2" />
          已安装
        </Button>
      </div>

      {/* Marketplace Tab */}
      {activeTab === 'marketplace' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                插件列表
              </CardTitle>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="搜索插件..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 pr-4 py-2 border rounded-md bg-white w-64"
                  />
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {filteredListings.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredListings.map((plugin) => (
                  <div key={plugin.plugin_id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-semibold text-lg">{plugin.plugin_name}</h3>
                        <p className="text-sm text-gray-500">v{plugin.version} by {plugin.author}</p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                        <span className="text-sm">{plugin.rating.toFixed(1)}</span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">{plugin.description}</p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={plugin.review_status as "error" | "success" | "warning" | "info" | "pending" | "unknown"} />
                        <span className="text-xs text-gray-500">{plugin.quality}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {plugin.review_status === 'approved' && (
                          <Button size="sm" onClick={() => handleDownloadPlugin(plugin.plugin_id)}>
                            <Download className="h-4 w-4 mr-1" />
                            安装
                          </Button>
                        )}
                        {plugin.review_status === 'pending' && (
                          <div className="flex gap-1">
                            <Button size="sm" variant="outline" onClick={() => handleApprovePlugin(plugin.plugin_id)}>
                              <CheckCircle className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => handleRejectPlugin(plugin.plugin_id)}>
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                      下载: {plugin.downloads} | 发布: {new Date(plugin.published_date).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="暂无插件"
                description={searchQuery ? "未找到匹配的插件" : "插件市场暂无可用插件"}
                action={!searchQuery && <Button onClick={() => setShowPublishModal(true)}>发布第一个插件</Button>}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Publish Tab */}
      {activeTab === 'publish' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              发布插件
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="发布插件"
              description="将你的插件发布到插件市场"
              action={<Button onClick={() => setShowPublishModal(true)}>开始发布</Button>}
            />
          </CardContent>
        </Card>
      )}

      {/* Installed Tab */}
      {activeTab === 'installed' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              已安装插件
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="已安装插件"
              description="查看和管理已安装的插件"
            />
          </CardContent>
        </Card>
      )}

      {/* Publish Plugin Modal */}
      <EnhancedModal
        open={showPublishModal}
        onOpenChange={setShowPublishModal}
        title="发布插件"
        size="lg"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">插件ID</label>
            <input
              type="text"
              value={publishData.plugin_id}
              onChange={(e) => setPublishData({ ...publishData, plugin_id: e.target.value })}
              placeholder="输入唯一插件ID"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">插件名称</label>
            <input
              type="text"
              value={publishData.plugin_name}
              onChange={(e) => setPublishData({ ...publishData, plugin_name: e.target.value })}
              placeholder="输入插件名称"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">版本</label>
            <input
              type="text"
              value={publishData.version}
              onChange={(e) => setPublishData({ ...publishData, version: e.target.value })}
              placeholder="输入版本号 (如 1.0.0)"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">作者</label>
            <input
              type="text"
              value={publishData.author}
              onChange={(e) => setPublishData({ ...publishData, author: e.target.value })}
              placeholder="输入作者名称"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea
              value={publishData.description}
              onChange={(e) => setPublishData({ ...publishData, description: e.target.value })}
              placeholder="输入插件描述"
              className="w-full px-3 py-2 border rounded-md bg-white min-h-[100px]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">质量等级</label>
            <select
              value={publishData.quality}
              onChange={(e) => setPublishData({ ...publishData, quality: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="community">社区</option>
              <option value="verified">验证</option>
              <option value="official">官方</option>
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowPublishModal(false)}>
              取消
            </Button>
            <Button onClick={handlePublishPlugin} disabled={publishPluginMutation.isPending}>
              {publishPluginMutation.isPending ? '发布中...' : '发布'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}