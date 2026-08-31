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
  Shield,
  BarChart3,
  Award,
  Zap,
  Users,
  Clock,
  Globe,
  GitBranch,
  FileText,
  Settings,
  AlertCircle
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

interface MarketplaceStats {
  total_plugins: number;
  total_downloads: number;
  total_reviews: number;
  active_categories: number;
  top_categories: Array<{ category: string; count: number }>;
  trending_plugins: PluginListing[];
  recent_updates: PluginListing[];
}

interface PluginAnalytics {
  plugin_id: string;
  daily_downloads: Array<{ date: string; count: number }>;
  user_demographics: Record<string, number>;
  rating_distribution: Record<string, number>;
}

export default function PluginMarketplaceAdvancedPage() {
  const [activeTab, setActiveTab] = useState<'browse' | 'analytics' | 'trending' | 'manage'>('browse');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedQuality, setSelectedQuality] = useState<string>('');
  const [selectedPlugin, setSelectedPlugin] = useState<PluginListing | null>(null);
  const [analyticsDialogOpen, setAnalyticsDialogOpen] = useState(false);
  const [pluginAnalytics, setPluginAnalytics] = useState<PluginAnalytics | null>(null);

  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  const debouncedSearch = useDebounce(searchQuery, 300);

  // 获取市场统计
  const { data: statsData, isLoading: statsLoading, refetch: refetchStats } = useQuery<MarketplaceStats>({
    queryKey: ['plugin-marketplace-stats'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/plugin/marketplace/statistics');
      return resp.data.data;
    },
    refetchInterval: 300000,
  });

  // 获取插件列表
  const { data: pluginsData, isLoading: pluginsLoading, refetch: refetchPlugins } = useQuery<{ items: PluginListing[]; total: number }>({
    queryKey: ['plugin-marketplace-plugins', selectedCategory, selectedQuality, debouncedSearch],
    queryFn: async () => {
      const params: any = { limit: 50, offset: 0 };
      if (selectedCategory) params.category = selectedCategory;
      if (selectedQuality) params.quality = selectedQuality;
      
      const resp = await api.get('/api/v1/plugin/marketplace/plugins', { params });
      return resp.data.data;
    },
    refetchInterval: 120000,
  });

  // 获取插件分析数据
  const { data: analyticsData, isLoading: analyticsLoading } = useQuery<PluginAnalytics>({
    queryKey: ['plugin-analytics', selectedPlugin?.plugin_id],
    queryFn: async () => {
      if (!selectedPlugin) return null;
      const resp = await api.get(`/api/v1/plugin/marketplace/plugins/${selectedPlugin.plugin_id}/analytics`);
      return resp.data.data;
    },
    enabled: !!selectedPlugin && analyticsDialogOpen,
  });

  const { isLoading: pageLoading, error: pageError } = useLoadingState(statsLoading || pluginsLoading);

  const handleViewAnalytics = async (plugin: PluginListing) => {
    setSelectedPlugin(plugin);
    setAnalyticsDialogOpen(true);
  };

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'certified':
        return 'bg-purple-100 text-purple-800';
      case 'verified':
        return 'bg-blue-100 text-blue-800';
      case 'community':
        return 'bg-gray-100 text-gray-800';
      case 'experimental':
        return 'bg-orange-100 text-orange-800';
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
    { key: 'analytics' as const, label: '市场分析', icon: BarChart3 },
    { key: 'trending' as const, label: '热门趋势', icon: TrendingUp },
    { key: 'manage' as const, label: '插件管理', icon: Settings },
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
          action={<Button onClick={() => { refetchStats(); refetchPlugins(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => { refetchStats(); refetchPlugins(); }}>重试</Button>}
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
            <h1 className="text-3xl font-bold text-gray-900">高级插件市场</h1>
            <p className="text-sm text-gray-500">插件市场分析、趋势洞察和高级管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchStats(); refetchPlugins(); }} variant="outline">
            刷新
          </Button>
        </div>
      </div>

      {/* 市场统计概览 */}
      {statsData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              市场概览
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 border rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <ShoppingBag className="h-5 w-5 text-[var(--accent-blue)]" />
                  <div className="text-sm text-gray-500">总插件数</div>
                </div>
                <div className="text-2xl font-bold text-[var(--accent-blue)]">
                  {statsData.total_plugins || 0}
                </div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Download className="h-5 w-5 text-[var(--accent-green)]" />
                  <div className="text-sm text-gray-500">总下载量</div>
                </div>
                <div className="text-2xl font-bold text-[var(--accent-green)]">
                  {statsData.total_downloads?.toLocaleString() || 0}
                </div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <MessageSquare className="h-5 w-5 text-[var(--accent-yellow)]" />
                  <div className="text-sm text-gray-500">总评论数</div>
                </div>
                <div className="text-2xl font-bold text-[var(--accent-yellow)]">
                  {statsData.total_reviews || 0}
                </div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Award className="h-5 w-5 text-[var(--accent-purple)]" />
                  <div className="text-sm text-gray-500">活跃分类</div>
                </div>
                <div className="text-2xl font-bold text-[var(--accent-purple)]">
                  {statsData.active_categories || 0}
                </div>
              </div>
            </div>

            {/* 热门分类 */}
            {statsData.top_categories && statsData.top_categories.length > 0 && (
              <div className="mt-4">
                <div className="text-sm font-medium mb-2">热门分类</div>
                <div className="flex flex-wrap gap-2">
                  {statsData.top_categories.map((item, idx) => (
                    <Badge key={idx} className={getCategoryColor(item.category)}>
                      {item.category} ({item.count})
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2 flex-wrap">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${
                  activeTab === tab.key
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
                    <option value="certified">认证</option>
                    <option value="verified">已验证</option>
                    <option value="community">社区</option>
                    <option value="experimental">实验性</option>
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
                          onClick={() => handleViewAnalytics(plugin)}
                          variant="outline"
                        >
                          <BarChart3 className="h-4 w-4" />
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

      {activeTab === 'analytics' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              市场分析
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* 分类分布 */}
              {statsData?.top_categories && (
                <div>
                  <h3 className="text-lg font-medium mb-4">分类分布</h3>
                  <div className="space-y-3">
                    {statsData.top_categories.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <div className="w-32 text-sm">{item.category}</div>
                        <div className="flex-1 bg-gray-200 rounded-full h-4">
                          <div
                            className="bg-[var(--accent-blue)] h-4 rounded-full"
                            style={{ width: `${(item.count / statsData.total_plugins) * 100}%` }}
                          />
                        </div>
                        <div className="w-16 text-sm text-right">{item.count}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 质量分布 */}
              <div>
                <h3 className="text-lg font-medium mb-4">插件质量分布</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 border rounded-lg text-center">
                    <Award className="h-8 w-8 mx-auto mb-2 text-purple-500" />
                    <div className="text-2xl font-bold">认证</div>
                    <div className="text-sm text-gray-500">Certified</div>
                  </div>
                  <div className="p-4 border rounded-lg text-center">
                    <Shield className="h-8 w-8 mx-auto mb-2 text-blue-500" />
                    <div className="text-2xl font-bold">已验证</div>
                    <div className="text-sm text-gray-500">Verified</div>
                  </div>
                  <div className="p-4 border rounded-lg text-center">
                    <Users className="h-8 w-8 mx-auto mb-2 text-gray-500" />
                    <div className="text-2xl font-bold">社区</div>
                    <div className="text-sm text-gray-500">Community</div>
                  </div>
                  <div className="p-4 border rounded-lg text-center">
                    <Zap className="h-8 w-8 mx-auto mb-2 text-orange-500" />
                    <div className="text-2xl font-bold">实验性</div>
                    <div className="text-sm text-gray-500">Experimental</div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'trending' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              热门趋势
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsData?.trending_plugins && statsData.trending_plugins.length > 0 ? (
              <div className="space-y-4">
                {statsData.trending_plugins.map((plugin, idx) => (
                  <div key={plugin.id} className="flex items-center gap-4 p-4 border rounded-lg">
                    <div className="flex items-center justify-center w-8 h-8 bg-[var(--accent-blue)] text-white rounded-full font-bold">
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <div className="font-medium">{plugin.plugin_name}</div>
                      <div className="text-sm text-gray-500">{plugin.description}</div>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <div className="flex items-center gap-1">
                        <Download className="h-4 w-4" />
                        <span>{plugin.download_count}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Star className="h-4 w-4 text-yellow-500" />
                        <span>{plugin.rating.toFixed(1)}</span>
                      </div>
                      <Badge className={getQualityColor(plugin.quality)}>
                        {plugin.quality}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="暂无热门插件"
                description="热门插件数据将定期更新"
              />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'manage' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              插件管理
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="插件管理功能"
              description="高级插件管理功能包括批量操作、审核流程、版本管理等"
              action={
                <Button onClick={() => setActiveTab('browse')}>
                  <ShoppingBag className="h-4 w-4 mr-2" />
                  浏览插件
                </Button>
              }
            />
          </CardContent>
        </Card>
      )}

      {/* 插件详情对话框 */}
      <Dialog open={!!selectedPlugin && !analyticsDialogOpen} onOpenChange={() => setSelectedPlugin(null)}>
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
                
                {selectedPlugin.documentation_url && (
                  <div>
                    <Button variant="outline" size="sm" asChild>
                      <a href={selectedPlugin.documentation_url} target="_blank" rel="noopener noreferrer">
                        <FileText className="h-4 w-4 mr-2" />
                        查看文档
                      </a>
                    </Button>
                  </div>
                )}
                
                {selectedPlugin.repository_url && (
                  <div>
                    <Button variant="outline" size="sm" asChild>
                      <a href={selectedPlugin.repository_url} target="_blank" rel="noopener noreferrer">
                        <GitBranch className="h-4 w-4 mr-2" />
                        源代码仓库
                      </a>
                    </Button>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* 分析数据对话框 */}
      <Dialog open={analyticsDialogOpen} onOpenChange={setAnalyticsDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              插件分析 - {selectedPlugin?.plugin_name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {analyticsLoading ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : analyticsData ? (
              <>
                {/* 下载趋势 */}
                <div>
                  <h3 className="text-lg font-medium mb-3">下载趋势</h3>
                  <div className="h-48 border rounded-lg p-4">
                    {analyticsData.daily_downloads && analyticsData.daily_downloads.length > 0 ? (
                      <div className="space-y-2">
                        {analyticsData.daily_downloads.slice(-7).map((item, idx) => (
                          <div key={idx} className="flex items-center gap-2 text-sm">
                            <div className="w-24">{item.date}</div>
                            <div className="flex-1 bg-gray-200 rounded-full h-4">
                              <div
                                className="bg-[var(--accent-green)] h-4 rounded-full"
                                style={{ width: `${Math.min((item.count / 100) * 100, 100)}%` }}
                              />
                            </div>
                            <div className="w-12 text-right">{item.count}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center text-gray-500">暂无数据</div>
                    )}
                  </div>
                </div>

                {/* 评分分布 */}
                <div>
                  <h3 className="text-lg font-medium mb-3">评分分布</h3>
                  <div className="grid grid-cols-5 gap-2">
                    {[5, 4, 3, 2, 1].map((star) => (
                      <div key={star} className="p-3 border rounded-lg text-center">
                        <div className="text-2xl font-bold">
                          {analyticsData.rating_distribution?.[star.toString()] || 0}
                        </div>
                        <div className="text-sm text-gray-500">
                          {star} 星
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 用户画像 */}
                <div>
                  <h3 className="text-lg font-medium mb-3">用户画像</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(analyticsData.user_demographics || {}).map(([key, value], idx) => (
                      <div key={idx} className="p-3 border rounded-lg text-center">
                        <div className="text-xl font-bold">{value}</div>
                        <div className="text-sm text-gray-500">{key}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <EmptyState
                title="暂无分析数据"
                description="该插件的分析数据尚未生成"
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
