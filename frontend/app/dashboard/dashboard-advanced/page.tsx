'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Layout, Settings, RefreshCw, Plus, Trash2, BarChart3, Table as TableIcon, Log, Alert as AlertIcon, Monitor, Move, Eye, EyeOff } from 'lucide-react';

interface DashboardWidget {
  id: string;
  widget_type: 'metric' | 'chart' | 'table' | 'log' | 'alert' | 'status';
  title: string;
  description?: string;
  config: Record<string, any>;
  data_source?: string;
  refresh_interval: number;
  position: Record<string, number>;
  size: Record<string, number>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
}

interface DashboardLayout {
  id: string;
  name: string;
  layout_type: 'grid' | 'flex' | 'custom';
  widgets: string[];
  is_default: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export default function DashboardAdvancedPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'widgets' | 'layouts'>('widgets');
  const [selectedWidget, setSelectedWidget] = useState<DashboardWidget | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [newWidgetData, setNewWidgetData] = useState({
    widget_type: 'metric' as const,
    title: '',
    description: '',
    data_source: '',
    refresh_interval: 30,
    enabled: true,
  });

  const debouncedSearch = useDebounce(searchTerm, 300);
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(false);
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // Fetch dashboard widgets
  const { data: dashboardWidgets, isLoading: widgetsLoading, error: widgetsError, refetch: refetchWidgets } = useQuery<DashboardWidget[]>({
    queryKey: ['dashboard-widgets'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/dashboard/widgets');
      return resp.data.widgets || resp.data || [];
    },
    refetchInterval: 60000,
  });

  // Fetch dashboard layouts
  const { data: dashboardLayouts, isLoading: layoutsLoading, error: layoutsError, refetch: refetchLayouts } = useQuery<DashboardLayout[]>({
    queryKey: ['dashboard-layouts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/dashboard/layouts');
      return resp.data.layouts || resp.data || [];
    },
    refetchInterval: 120000,
  });

  // Create widget mutation
  const createWidgetMutation = useMutation({
    mutationFn: async (widgetData: typeof newWidgetData) => {
      const resp = await api.post('/api/v1/dashboard/widgets', widgetData);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Widget created successfully');
      setIsCreateDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ['dashboard-widgets'] });
    },
    onError: (error: any) => {
      showError(`Failed to create widget: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete widget mutation
  const deleteWidgetMutation = useMutation({
    mutationFn: async (widgetId: string) => {
      const resp = await api.delete(`/api/v1/dashboard/widgets/${widgetId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Widget deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['dashboard-widgets'] });
    },
    onError: (error: any) => {
      showError(`Failed to delete widget: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Toggle widget mutation
  const toggleWidgetMutation = useMutation({
    mutationFn: async ({ widgetId, enabled }: { widgetId: string; enabled: boolean }) => {
      const resp = await api.patch(`/api/v1/dashboard/widgets/${widgetId}`, { enabled });
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Widget status updated');
      queryClient.invalidateQueries({ queryKey: ['dashboard-widgets'] });
    },
    onError: (error: any) => {
      showError(`Failed to update widget: ${error.response?.data?.detail || error.message}`);
    },
  });

  useEffect(() => {
    if (widgetsError) {
      setPageError(widgetsError as Error);
      showError('Failed to load dashboard widgets');
    }
  }, [widgetsError, setPageError, showError]);

  const filteredWidgets = dashboardWidgets?.filter((widget) => {
    if (typeFilter !== 'all' && widget.widget_type !== typeFilter) return false;
    if (debouncedSearch && !widget.title.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  }) || [];

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'metric':
        return <Monitor className="h-4 w-4" />;
      case 'chart':
        return <BarChart3 className="h-4 w-4" />;
      case 'table':
        return <TableIcon className="h-4 w-4" />;
      case 'log':
        return <Log className="h-4 w-4" />;
      case 'alert':
        return <AlertIcon className="h-4 w-4" />;
      case 'status':
        return <Monitor className="h-4 w-4" />;
      default:
        return <Layout className="h-4 w-4" />;
    }
  };

  const getLayoutTypeColor = (type: string) => {
    switch (type) {
      case 'grid':
        return 'bg-blue-100 text-blue-800';
      case 'flex':
        return 'bg-green-100 text-green-800';
      case 'custom':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleCreateWidget = () => {
    if (!newWidgetData.title) {
      showError('Please enter widget title');
      return;
    }
    createWidgetMutation.mutate(newWidgetData);
  };

  const handleDeleteWidget = (widgetId: string) => {
    if (!window.confirm('Are you sure you want to delete this widget?')) return;
    deleteWidgetMutation.mutate(widgetId);
  };

  const handleToggleWidget = (widgetId: string, currentEnabled: boolean) => {
    toggleWidgetMutation.mutate({ widgetId, enabled: !currentEnabled });
  };

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
          description="无法加载仪表板数据，请稍后重试"
          action={<Button onClick={() => refetchWidgets()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchWidgets()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Layout className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">仪表板高级</h1>
            <p className="text-sm text-gray-500">小部件、布局和仪表板配置管理</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchWidgets()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            创建小部件
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="widgets">
            <Monitor className="h-4 w-4 mr-2" />
            小部件
          </TabsTrigger>
          <TabsTrigger value="layouts">
            <Layout className="h-4 w-4 mr-2" />
            布局
          </TabsTrigger>
        </TabsList>

        <TabsContent value="widgets" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Monitor className="h-5 w-5" />
                  小部件管理
                </span>
                <div className="flex gap-2">
                  <Input
                    placeholder="搜索小部件..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-64"
                  />
                  <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                    <option value="all">全部类型</option>
                    <option value="metric">指标</option>
                    <option value="chart">图表</option>
                    <option value="table">表格</option>
                    <option value="log">日志</option>
                    <option value="alert">告警</option>
                    <option value="status">状态</option>
                  </Select>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {widgetsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : filteredWidgets.length === 0 ? (
                <EmptyState
                  title="没有小部件"
                  description="点击创建小部件开始配置仪表板"
                  action={<Button onClick={() => setIsCreateDialogOpen(true)}>创建小部件</Button>}
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>标题</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>数据源</TableHead>
                      <TableHead>刷新间隔</TableHead>
                      <TableHead>位置</TableHead>
                      <TableHead>大小</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建者</TableHead>
                      <TableHead>更新时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredWidgets.map((widget) => (
                      <TableRow key={widget.id}>
                        <TableCell className="font-mono text-sm">{widget.id}</TableCell>
                        <TableCell className="font-medium">{widget.title}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getTypeIcon(widget.widget_type)}
                            <span className="capitalize">{widget.widget_type}</span>
                          </div>
                        </TableCell>
                        <TableCell>{widget.data_source || '-'}</TableCell>
                        <TableCell>{widget.refresh_interval}s</TableCell>
                        <TableCell>
                          {widget.position.x !== undefined ? `(${widget.position.x}, ${widget.position.y})` : '-'}
                        </TableCell>
                        <TableCell>
                          {widget.size.width !== undefined ? `${widget.size.width}x${widget.size.height}` : '-'}
                        </TableCell>
                        <TableCell>
                          {widget.enabled ? (
                            <Badge className="bg-green-100 text-green-800">启用</Badge>
                          ) : (
                            <Badge className="bg-gray-100 text-gray-800">禁用</Badge>
                          )}
                        </TableCell>
                        <TableCell>{widget.created_by}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(widget.updated_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleWidget(widget.id, widget.enabled)}
                            >
                              {widget.enabled ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedWidget(widget)}
                            >
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteWidget(widget.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="layouts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layout className="h-5 w-5" />
                布局管理
              </CardTitle>
            </CardHeader>
            <CardContent>
              {layoutsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner />
                </div>
              ) : !dashboardLayouts || dashboardLayouts.length === 0 ? (
                <EmptyState title="无布局" description="暂无布局记录" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>布局类型</TableHead>
                      <TableHead>小部件数</TableHead>
                      <TableHead>默认</TableHead>
                      <TableHead>创建者</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>更新时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dashboardLayouts.map((layout) => (
                      <TableRow key={layout.id}>
                        <TableCell className="font-mono text-sm">{layout.id}</TableCell>
                        <TableCell className="font-medium">{layout.name}</TableCell>
                        <TableCell>
                          <Badge className={getLayoutTypeColor(layout.layout_type)}>
                            {layout.layout_type}
                          </Badge>
                        </TableCell>
                        <TableCell>{layout.widgets.length}</TableCell>
                        <TableCell>
                          {layout.is_default ? (
                            <Badge className="bg-blue-100 text-blue-800">是</Badge>
                          ) : (
                            <Badge className="bg-gray-100 text-gray-800">否</Badge>
                          )}
                        </TableCell>
                        <TableCell>{layout.created_by}</TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(layout.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">
                          {new Date(layout.updated_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm">
                              <Settings className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Move className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建小部件</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">标题</label>
              <Input
                value={newWidgetData.title}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, title: e.target.value })}
                placeholder="输入小部件标题"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Input
                value={newWidgetData.description}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, description: e.target.value })}
                placeholder="小部件描述"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">类型</label>
              <Select
                value={newWidgetData.widget_type}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, widget_type: e.target.value as any })}
              >
                <option value="metric">指标</option>
                <option value="chart">图表</option>
                <option value="table">表格</option>
                <option value="log">日志</option>
                <option value="alert">告警</option>
                <option value="status">状态</option>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">数据源</label>
              <Input
                value={newWidgetData.data_source}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, data_source: e.target.value })}
                placeholder="数据源URL或API端点"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">刷新间隔(秒)</label>
              <Input
                type="number"
                value={newWidgetData.refresh_interval}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, refresh_interval: parseInt(e.target.value) })}
                placeholder="刷新间隔"
              />
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={newWidgetData.enabled}
                onChange={(e) => setNewWidgetData({ ...newWidgetData, enabled: e.target.checked })}
              />
              <span className="text-sm">启用小部件</span>
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateWidget} disabled={createWidgetMutation.isPending}>
              {createWidgetMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
