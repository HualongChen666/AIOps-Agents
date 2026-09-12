'use client'

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Package, RefreshCw, Download, CheckCircle, Star, Plus, Search, Trash2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface PluginListing {
  id: number;
  plugin_id: string;
  plugin_name: string;
  version: string;
  description: string;
  author: string;
  category: string;
  quality: string;
  download_count: number;
  rating: number;
  review_count: number;
  enabled: boolean;
  created_at: string;
}

interface InstalledPlugin {
  id: number;
  plugin_id: string;
  installed_version: string;
  status: string;
  installation_date: string;
}

export default function PluginMarketplacePage() {
  const [activeTab, setActiveTab] = useState<'marketplace' | 'installed'>('marketplace');
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [publishData, setPublishData] = useState({
    plugin_id: '',
    plugin_name: '',
    version: '1.0.0',
    description: '',
    author: '',
    category: 'general',
    quality: 'community',
    download_url: '',
  });

  const queryClient = useQueryClient();

  const { data: listingsData, isLoading: listingsLoading, error: listingsError, refetch: refetchListings } = useQuery({
    queryKey: ['plugin-marketplace-listings'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/plugin-marketplace/plugins', { params: { limit: 100 } });
      return resp.data.data;
    },
    refetchInterval: 120000,
  });

  const { data: installedData, isLoading: installedLoading, refetch: refetchInstalled } = useQuery({
    queryKey: ['plugin-marketplace-installed'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/plugin-marketplace/plugins/installed');
      return resp.data.data;
    },
    refetchInterval: 120000,
  });

  const publishPluginMutation = useMutation({
    mutationFn: async (data: typeof publishData) => {
      const resp = await api.post('/api/v1/plugin-marketplace/plugins', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugin-marketplace-listings'] });
      setShowPublishModal(false);
      showSuccess('插件已提交，等待审核');
    },
    onError: (error: any) => showError(`发布失败: ${error.response?.data?.detail || error.message}`),
  });

  const installPluginMutation = useMutation({
    mutationFn: async (plugin: PluginListing) => {
      const resp = await api.post(`/api/v1/plugin-marketplace/plugins/${plugin.plugin_id}/install`, {
        plugin_id: plugin.plugin_id,
        installed_version: plugin.version,
      });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugin-marketplace-listings'] });
      queryClient.invalidateQueries({ queryKey: ['plugin-marketplace-installed'] });
      showSuccess('插件安装成功');
    },
    onError: (error: any) => showError(`安装失败: ${error.response?.data?.detail || error.message}`),
  });

  const uninstallPluginMutation = useMutation({
    mutationFn: async (pluginId: string) => {
      const resp = await api.delete(`/api/v1/plugin-marketplace/plugins/installed/${pluginId}`);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugin-marketplace-installed'] });
      showSuccess('插件已卸载');
    },
    onError: (error: any) => showError(`卸载失败: ${error.response?.data?.detail || error.message}`),
  });

  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(
    listingsLoading || installedLoading
  );

  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  useEffect(() => {
    if (listingsError) {
      showError('Failed to load plugin marketplace data');
      setPageError(listingsError as Error);
    }
  }, [listingsError, showError, setPageError]);

  const listings: PluginListing[] = listingsData?.items || [];
  const installed: InstalledPlugin[] = installedData?.items || [];
  const stats = {
    total_plugins: listings.length,
    enabled_plugins: listings.filter((p) => p.enabled).length,
    installed_plugins: installed.length,
    total_downloads: listings.reduce((s, p) => s + (p.download_count || 0), 0),
  };

  const filteredListings = listings.filter((plugin) =>
    plugin.plugin_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (plugin.description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (plugin.author || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleRefresh = () => {
    refetchListings();
    refetchInstalled();
  };

  if (pageLoading) {
    return <div className="flex items-center justify-center min-h-screen"><LoadingSpinner size="lg" /></div>;
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={<EmptyState title="加载失败" description="无法加载插件市场数据" action={<Button onClick={handleRefresh}>重试</Button>} />}>
        <EmptyState title="加载失败" description={pageError.message} action={<Button onClick={handleRefresh}>重试</Button>} />
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
          <Button onClick={handleRefresh} variant="outline"><RefreshCw className="h-4 w-4 mr-2" />刷新</Button>
          <Button onClick={() => setShowPublishModal(true)}><Plus className="h-4 w-4 mr-2" />发布插件</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card><CardHeader><CardTitle className="text-sm">总插件数</CardTitle></CardHeader><CardContent><p className="text-3xl font-bold text-blue-600">{stats.total_plugins}</p></CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">已启用</CardTitle></CardHeader><CardContent><p className="text-3xl font-bold text-green-600">{stats.enabled_plugins}</p></CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">已安装</CardTitle></CardHeader><CardContent><p className="text-3xl font-bold text-purple-600">{stats.installed_plugins}</p></CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">总下载</CardTitle></CardHeader><CardContent><p className="text-3xl font-bold text-orange-600">{stats.total_downloads}</p></CardContent></Card>
      </div>

      <div className="flex gap-2 border-b">
        <Button variant={activeTab === 'marketplace' ? 'default' : 'ghost'} onClick={() => setActiveTab('marketplace')}><Package className="h-4 w-4 mr-2" />插件市场</Button>
        <Button variant={activeTab === 'installed' ? 'default' : 'ghost'} onClick={() => setActiveTab('installed')}><CheckCircle className="h-4 w-4 mr-2" />已安装</Button>
      </div>

      {activeTab === 'marketplace' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2"><Package className="h-5 w-5" />插件列表</CardTitle>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input type="text" placeholder="搜索插件..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10 pr-4 py-2 border rounded-md bg-white w-64" />
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
                      <div className="flex items-center gap-1"><Star className="h-4 w-4 text-yellow-500 fill-yellow-500" /><span className="text-sm">{(plugin.rating || 0).toFixed(1)}</span></div>
                    </div>
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">{plugin.description}</p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={plugin.enabled ? 'success' : 'warning'} />
                        <span className="text-xs text-gray-500">{plugin.quality}</span>
                      </div>
                      <Button size="sm" onClick={() => installPluginMutation.mutate(plugin)} disabled={installPluginMutation.isPending}>
                        <Download className="h-4 w-4 mr-1" />安装
                      </Button>
                    </div>
                    <div className="mt-2 text-xs text-gray-500">下载: {plugin.download_count} | 评分次数: {plugin.review_count}</div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="暂无插件" description={searchQuery ? '未找到匹配的插件' : '插件市场暂无可用插件'} action={!searchQuery && <Button onClick={() => setShowPublishModal(true)}>发布第一个插件</Button>} />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'installed' && (
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><CheckCircle className="h-5 w-5" />已安装插件（{installed.length}）</CardTitle></CardHeader>
          <CardContent>
            {installed.length === 0 ? (
              <EmptyState title="暂无已安装插件" description="从插件市场安装插件后会显示在这里" />
            ) : (
              <div className="space-y-2">
                {installed.map((p) => (
                  <div key={p.id} className="border rounded-lg p-3 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{p.plugin_id}</span>
                        <StatusBadge status={p.status === 'active' || p.status === 'installed' ? 'success' : 'warning'} />
                      </div>
                      <div className="text-xs text-gray-500">版本 {p.installed_version} | {p.installation_date ? new Date(p.installation_date).toLocaleString() : ''}</div>
                    </div>
                    <Button size="sm" variant="outline" onClick={() => uninstallPluginMutation.mutate(p.plugin_id)} disabled={uninstallPluginMutation.isPending}>
                      <Trash2 className="h-4 w-4 mr-1" />卸载
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <EnhancedModal open={showPublishModal} onOpenChange={setShowPublishModal} title="发布插件" size="lg">
        <div className="space-y-4">
          {([
            ['plugin_id', '插件ID', '输入唯一插件ID'],
            ['plugin_name', '插件名称', '输入插件名称'],
            ['version', '版本', '输入版本号 (如 1.0.0)'],
            ['author', '作者', '输入作者名称'],
            ['download_url', '下载 URL', 'https://.../plugin.zip'],
          ] as const).map(([key, label, ph]) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input type="text" value={(publishData as any)[key]} onChange={(e) => setPublishData({ ...publishData, [key]: e.target.value })} placeholder={ph} className="w-full px-3 py-2 border rounded-md bg-white" />
            </div>
          ))}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea value={publishData.description} onChange={(e) => setPublishData({ ...publishData, description: e.target.value })} className="w-full px-3 py-2 border rounded-md bg-white min-h-[100px]" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">分类</label>
              <select value={publishData.category} onChange={(e) => setPublishData({ ...publishData, category: e.target.value })} className="w-full px-3 py-2 border rounded-md bg-white">
                {['general', 'monitoring', 'alerting', 'automation', 'analytics', 'security', 'performance', 'integration'].map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">质量等级</label>
              <select value={publishData.quality} onChange={(e) => setPublishData({ ...publishData, quality: e.target.value })} className="w-full px-3 py-2 border rounded-md bg-white">
                <option value="community">社区</option><option value="verified">验证</option><option value="official">官方</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowPublishModal(false)}>取消</Button>
            <Button onClick={() => publishPluginMutation.mutate(publishData)} disabled={publishPluginMutation.isPending}>
              {publishPluginMutation.isPending ? '发布中...' : '发布'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}
