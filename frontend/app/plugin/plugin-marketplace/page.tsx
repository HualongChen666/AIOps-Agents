'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import {
  ShoppingBag,
  Search,
  Download,
  Star,
  Upload,
  Filter,
  CheckCircle,
  XCircle,
  Trash2,
  Eye,
  Heart,
  MessageSquare,
  TrendingUp,
  Shield
} from 'lucide-react';

interface PluginListing {
  id: string;
  plugin_id: string;
  plugin_name: string;
  version: string;
  description: string;
  author: string;
  category: string;
  tags: string[];
  price: number | null;
  quality: string;
  download_url: string;
  screenshot_urls: string[];
  documentation_url: string | null;
  repository_url: string | null;
  download_count: number;
  rating: number;
  review_count: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

interface InstalledPlugin {
  id: string;
  plugin_id: string;
  installed_version: string;
  installation_date: string;
  status: string;
  configuration: Record<string, any>;
  enabled: boolean;
  updated_at: string;
}

interface PluginReview {
  id: string;
  plugin_id: string;
  reviewer_id: string;
  reviewer_name: string;
  rating: number;
  review_text: string;
  created_at: string;
}

export default function PluginMarketplacePage() {
  const [activeTab, setActiveTab] = useState<'browse' | 'installed' | 'upload'>('browse');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedQuality, setSelectedQuality] = useState<string>('');
  const [selectedPlugin, setSelectedPlugin] = useState<PluginListing | null>(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    plugin_id: '',
    plugin_name: '',
    version: '1.0.0',
    description: '',
    author: '',
    category: 'general',
    tags: '',
    price: '',
    quality: 'community',
    download_url: '',
    documentation_url: '',
    repository_url: '',
  });
  const [reviewForm, setReviewForm] = useState({
    rating: 5,
    review_text: '',
  });

  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  const debouncedSearch = useDebounce(searchQuery, 300);

  // 获取插件列表
  const { data: pluginsData, isLoading: pluginsLoading, refetch: refetchPlugins } = useQuery<{ items: PluginListing[]; total: number }>({
    queryKey: ['plugin-marketplace-plugins', selectedCategory, selectedQuality, debouncedSearch],
    queryFn: async () => {
      const params: any = { limit: 50, offset: 0 };
      if (selectedCategory) params.category = selectedCategory;
      if (selectedQuality) params.quality = selectedQuality;

      const resp = await api.get('/api/v1/plugin-marketplace/plugins', { params });
      return resp.data.data;
    },
    refetchInterval: 120000,
  });

  // 获取已安装插件
  const { data: installedData, isLoading: installedLoading, refetch: refetchInstalled } = useQuery<{ items: InstalledPlugin[]; total: number }>({
    queryKey: ['plugin-marketplace-installed'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/plugin-marketplace/plugins/installed');
      return resp.data.data;
    },
    refetchInterval: 60000,
  });

  const { isLoading: pageLoading, error: pageError } = useLoadingState(pluginsLoading || installedLoading);

  const handleInstallPlugin = async (pluginId: string, version: string) => {
    try {
      const resp = await api.post(`/api/v1/plugin-marketplace/plugins/${pluginId}/install`, {
        plugin_id: pluginId,
        installed_version: version,
        configuration: {},
      });

      if (resp.data.status === 'success') {
        showSuccess('插件安装成功');
        refetchInstalled();
        refetchPlugins();
      } else {
        showError('插件安装失败');
      }
    } catch (error: any) {
      showError(`安装失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleUninstallPlugin = async (pluginId: string) => {
    if (!window.confirm('确定要卸载此插件吗？')) return;

    try {
      const resp = await api.delete(`/api/v1/plugin-marketplace/plugins/installed/${pluginId}`);

      if (resp.data.status === 'success') {
        showSuccess('插件卸载成功');
        refetchInstalled();
      } else {
        showError('插件卸载失败');
      }
    } catch (error: any) {
      showError(`卸载失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleUploadPlugin = async () => {
    try {
      const request = {
        plugin_id: uploadForm.plugin_id,
        plugin_name: uploadForm.plugin_name,
        version: uploadForm.version,
        description: uploadForm.description,
        author: uploadForm.author,
        category: uploadForm.category,
        tags: uploadForm.tags ? uploadForm.tags.split(',').map(t => t.trim()) : [],
        price: uploadForm.price ? parseFloat(uploadForm.price) : null,
        quality: uploadForm.quality,
        download_url: uploadForm.download_url,
        documentation_url: uploadForm.documentation_url || null,
        repository_url: uploadForm.repository_url || null,
      };

      const resp = await api.post('/api/v1/plugin-marketplace/plugins', request);

      if (resp.data.status === 'success') {
        showSuccess('插件上传成功，等待审核');
        setUploadDialogOpen(false);
        setUploadForm({
          plugin_id: '',
          plugin_name: '',
          version: '1.0.0',
          description: '',
          author: '',
          category: 'general',
          tags: '',
          price: '',
          quality: 'community',
          download_url: '',
          documentation_url: '',
          repository_url: '',
        });
        refetchPlugins();
      } else {
        showError('插件上传失败');
      }
    } catch (error: any) {
      showError(`上传失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleAddReview = async () => {
    if (!selectedPlugin) return;

    try {
      const request = {
        plugin_id: selectedPlugin.plugin_id,
        reviewer_id: 'user-1', // TODO: 从用户上下文获取
        reviewer_name: 'Current User', // TODO: 从用户上下文获取
        rating: reviewForm.rating,
        review_text: reviewForm.review_text || null,
      };

      const resp = await api.post(`/api/v1/plugin-marketplace/plugins/${selectedPlugin.plugin_id}/reviews`, request);

      if (resp.data.status === 'success') {
        showSuccess('评论添加成功');
        setReviewDialogOpen(false);
        setReviewForm({ rating: 5, review_text: '' });
        refetchPlugins();
      } else {
        showError('评论添加失败');
      }
    } catch (error: any) {
      showError(`添加评论失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'official':
        return 'bg-purple-100 text-purple-800';
      case 'verified':
        return 'bg-blue-100 text-blue-800';
      case 'community':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      monitoring: 'bg-blue-100 text-blue-800',
      alerting: 'bg-red-100 text-red-800',
      automation: 'bg-green-100 text-green-800',
      analytics: 'bg-purple-100 text-purple-800',
      security: 'bg-yellow-100 text-yellow-800',
      performance: 'bg-cyan-100 text-cyan-800',
      integration: 'bg-indigo-100 text-indigo-800',
      general: 'bg-gray-100 text-gray-800',
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  const tabs = [
    { key: 'browse' as const, label: '浏览插件', icon: ShoppingBag },
    { key: 'installed' as const, label: '已安装', icon: Download },
    { key: 'upload' as const, label: '上传插件', icon: Upload },
  ];

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
          action={<Button onClick={() => { refetchPlugins(); refetchInstalled(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => { refetchPlugins(); refetchInstalled(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShoppingBag className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">插件市场</h1>
            <p className="text-sm text-gray-500">浏览、安装和管理插件</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchPlugins(); refetchInstalled(); }} variant="outline">
            刷新
          </Button>
          <Button onClick={() => setUploadDialogOpen(true)}>
            <Upload className="h-4 w-4 mr-2" />
            上传插件
          </Button>
        </div>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${activeTab === tab.key
                    ? 'bg-[var(--accent-blue)] text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {activeTab === 'browse' && (
        <>
          {/* 筛选器 */}
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
                  <div className="flex gap-2">
                    <Input
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="搜索插件名称或描述"
                    />
                    <Search className="h-4 w-4 text-gray-400 mt-2" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">分类</label>
                  <Select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                  >
                    <option value="">全部分类</option>
                    <option value="general">通用</option>
                    <option value="monitoring">监控</option>
                    <option value="alerting">告警</option>
                    <option value="automation">自动化</option>
                    <option value="analytics">分析</option>
                    <option value="security">安全</option>
                    <option value="performance">性能</option>
                    <option value="integration">集成</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">质量</label>
                  <Select
                    value={selectedQuality}
                    onChange={(e) => setSelectedQuality(e.target.value)}
                  >
                    <option value="">全部质量</option>
                    <option value="official">官方</option>
                    <option value="verified">已验证</option>
                    <option value="community">社区</option>
                  </Select>
                </div>
                <div className="flex items-end">
                  <Button onClick={() => refetchPlugins()} variant="outline">
                    <Filter className="h-4 w-4 mr-2" />
                    应用筛选
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 插件列表 */}
          <Card>
            <CardHeader>
              <CardTitle>
                插件列表 {pluginsData && `(${pluginsData.total || 0})`}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {pluginsData && pluginsData.items && pluginsData.items.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {pluginsData.items.map((plugin) => (
                    <div key={plugin.id} className="border rounded-lg p-4 hover:shadow-md transition">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg">{plugin.plugin_name}</h3>
                          <div className="text-sm text-gray-500">v{plugin.version} by {plugin.author}</div>
                        </div>
                        <Badge className={getQualityColor(plugin.quality)}>
                          {plugin.quality}
                        </Badge>
                      </div>

                      <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                        {plugin.description}
                      </p>

                      <div className="flex flex-wrap gap-1 mb-3">
                        <Badge className={getCategoryColor(plugin.category)}>
                          {plugin.category}
                        </Badge>
                        {plugin.tags?.slice(0, 3).map((tag, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>

                      <div className="flex items-center justify-between text-sm text-gray-500 mb-3">
                        <div className="flex items-center gap-1">
                          <Star className="h-4 w-4 text-yellow-500" />
                          <span>{plugin.rating.toFixed(1)}</span>
                          <span>({plugin.review_count})</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Download className="h-4 w-4" />
                          <span>{plugin.download_count}</span>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => setSelectedPlugin(plugin)}
                          variant="outline"
                          className="flex-1"
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          详情
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleInstallPlugin(plugin.plugin_id, plugin.version)}
                          className="flex-1"
                        >
                          <Download className="h-4 w-4 mr-1" />
                          安装
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="没有找到插件"
                  description="尝试调整筛选条件或搜索关键词"
                />
              )}
            </CardContent>
          </Card>
        </>
      )}

      {activeTab === 'installed' && (
        <Card>
          <CardHeader>
            <CardTitle>
              已安装插件 {installedData && `(${installedData.total || 0})`}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {installedData && installedData.items && installedData.items.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>插件ID</TableHead>
                    <TableHead>版本</TableHead>
                    <TableHead>安装日期</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {installedData.items.map((plugin) => (
                    <TableRow key={plugin.id}>
                      <TableCell className="font-mono text-sm">{plugin.plugin_id}</TableCell>
                      <TableCell>{plugin.installed_version}</TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(plugin.installation_date).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge variant={plugin.enabled ? 'default' : 'secondary'}>
                          {plugin.enabled ? '已启用' : '已禁用'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleUninstallPlugin(plugin.plugin_id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyState
                title="没有已安装的插件"
                description="从插件市场浏览并安装插件"
                action={
                  <Button onClick={() => setActiveTab('browse')}>
                    <ShoppingBag className="h-4 w-4 mr-2" />
                    浏览插件
                  </Button>
                }
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'upload' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              上传插件
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">插件ID *</label>
                  <Input
                    value={uploadForm.plugin_id}
                    onChange={(e) => setUploadForm({ ...uploadForm, plugin_id: e.target.value })}
                    placeholder="例如: my-custom-plugin"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">插件名称 *</label>
                  <Input
                    value={uploadForm.plugin_name}
                    onChange={(e) => setUploadForm({ ...uploadForm, plugin_name: e.target.value })}
                    placeholder="例如: My Custom Plugin"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">版本 *</label>
                  <Input
                    value={uploadForm.version}
                    onChange={(e) => setUploadForm({ ...uploadForm, version: e.target.value })}
                    placeholder="例如: 1.0.0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">作者 *</label>
                  <Input
                    value={uploadForm.author}
                    onChange={(e) => setUploadForm({ ...uploadForm, author: e.target.value })}
                    placeholder="插件作者"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">分类 *</label>
                  <Select
                    value={uploadForm.category}
                    onChange={(e) => setUploadForm({ ...uploadForm, category: e.target.value })}
                  >
                    <option value="general">通用</option>
                    <option value="monitoring">监控</option>
                    <option value="alerting">告警</option>
                    <option value="automation">自动化</option>
                    <option value="analytics">分析</option>
                    <option value="security">安全</option>
                    <option value="performance">性能</option>
                    <option value="integration">集成</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">质量</label>
                  <Select
                    value={uploadForm.quality}
                    onChange={(e) => setUploadForm({ ...uploadForm, quality: e.target.value })}
                  >
                    <option value="community">社区</option>
                    <option value="verified">已验证</option>
                    <option value="official">官方</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">价格 (可选)</label>
                  <Input
                    value={uploadForm.price}
                    onChange={(e) => setUploadForm({ ...uploadForm, price: e.target.value })}
                    placeholder="留空表示免费"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">下载URL *</label>
                  <Input
                    value={uploadForm.download_url}
                    onChange={(e) => setUploadForm({ ...uploadForm, download_url: e.target.value })}
                    placeholder="插件下载链接"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">描述 *</label>
                  <Textarea
                    value={uploadForm.description}
                    onChange={(e) => setUploadForm({ ...uploadForm, description: e.target.value })}
                    placeholder="插件功能描述"
                    rows={3}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">标签 (逗号分隔)</label>
                  <Input
                    value={uploadForm.tags}
                    onChange={(e) => setUploadForm({ ...uploadForm, tags: e.target.value })}
                    placeholder="例如: monitoring, alerts, automation"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">文档URL (可选)</label>
                  <Input
                    value={uploadForm.documentation_url}
                    onChange={(e) => setUploadForm({ ...uploadForm, documentation_url: e.target.value })}
                    placeholder="文档链接"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">仓库URL (可选)</label>
                  <Input
                    value={uploadForm.repository_url}
                    onChange={(e) => setUploadForm({ ...uploadForm, repository_url: e.target.value })}
                    placeholder="源代码仓库链接"
                  />
                </div>
              </div>
              <Button onClick={handleUploadPlugin} className="w-full">
                <Upload className="h-4 w-4 mr-2" />
                上传插件
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 插件详情对话框 */}
      <Dialog open={!!selectedPlugin} onOpenChange={() => setSelectedPlugin(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          {selectedPlugin && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Eye className="h-5 w-5" />
                  {selectedPlugin.plugin_name}
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Badge className={getQualityColor(selectedPlugin.quality)}>
                    {selectedPlugin.quality}
                  </Badge>
                  <Badge className={getCategoryColor(selectedPlugin.category)}>
                    {selectedPlugin.category}
                  </Badge>
                  <Badge variant="outline">v{selectedPlugin.version}</Badge>
                </div>

                <p className="text-gray-700">{selectedPlugin.description}</p>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">作者:</span> {selectedPlugin.author}
                  </div>
                  <div>
                    <span className="text-gray-500">下载次数:</span> {selectedPlugin.download_count}
                  </div>
                  <div className="flex items-center gap-1">
                    <Star className="h-4 w-4 text-yellow-500" />
                    <span className="text-gray-500">评分:</span> {selectedPlugin.rating.toFixed(1)} ({selectedPlugin.review_count} 评论)
                  </div>
                  <div>
                    <span className="text-gray-500">更新时间:</span> {new Date(selectedPlugin.updated_at).toLocaleString()}
                  </div>
                </div>

                {selectedPlugin.tags && selectedPlugin.tags.length > 0 && (
                  <div>
                    <div className="text-sm font-medium mb-2">标签:</div>
                    <div className="flex flex-wrap gap-1">
                      {selectedPlugin.tags.map((tag, idx) => (
                        <Badge key={idx} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    onClick={() => handleInstallPlugin(selectedPlugin.plugin_id, selectedPlugin.version)}
                    className="flex-1"
                  >
                    <Download className="h-4 w-4 mr-2" />
                    安装插件
                  </Button>
                  <Button
                    onClick={() => {
                      setReviewDialogOpen(true);
                      setSelectedPlugin(selectedPlugin);
                    }}
                    variant="outline"
                  >
                    <MessageSquare className="h-4 w-4 mr-2" />
                    添加评论
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* 评论对话框 */}
      <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              添加评论
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">评分</label>
              <Select
                value={reviewForm.rating.toString()}
                onChange={(e) => setReviewForm({ ...reviewForm, rating: parseInt(e.target.value) })}
              >
                <option value="5">5 星 - 优秀</option>
                <option value="4">4 星 - 良好</option>
                <option value="3">3 星 - 一般</option>
                <option value="2">2 星 - 较差</option>
                <option value="1">1 星 - 很差</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">评论内容</label>
              <Textarea
                value={reviewForm.review_text}
                onChange={(e) => setReviewForm({ ...reviewForm, review_text: e.target.value })}
                placeholder="分享您的使用体验..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReviewDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleAddReview}>
              <MessageSquare className="h-4 w-4 mr-2" />
              提交评论
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
